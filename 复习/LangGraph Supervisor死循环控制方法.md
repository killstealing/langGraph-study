# LangGraph Supervisor 多代理死循环控制方法

> 场景：Supervisor（编排者）模式下，LLM 解决不了问题时，会一直往 worker 派活、不停循环，永远不说 FINISH。
> 核心原因：Supervisor 模式没有「强制结束」机制，全靠 LLM 自觉判断何时 FINISH。

## 核心思想

控制死循环的本质是**显式终止条件（explicit termination）**。做法是**多层兜底**，从底层硬限制到高层智能检测 + 人工兜底。

---

## 六层方法

### ① 内置硬限制 `recursion_limit`

LangGraph 自带，一行配置，超了抛 `GraphRecursionError`。**最后一道防线，永远建议加上。**

```python
from langgraph.errors import GraphRecursionError

try:
    result = graph.invoke({"messages": ["..."]}, config={"recursion_limit": 10})
except GraphRecursionError:
    print("达到最大步数，已停止")
```

`astream` 同理，把 `config={"recursion_limit": 10}` 传进去即可。

---

### ② 步数预算（count 计数器）

显式「最多跑 N 轮」，最基础的一层。

```python
class AgentState(MessagesState):
    next: str
    count: int

def supervisor(state: AgentState):
    count = state.get('count', 0) + 1
    if count > 10:                                    # ← 上限
        return {'next': 'FINISH', 'count': count}
    ...
    return {'next': response['next'], 'count': count}
```

---

### ③ 卡死检测（stall detection，最聪明）

**核心**：连续好几次派同一个 worker = 没进展，提前停，不用等跑满 N 轮。
（Magentic-One 的 Progress Ledger 就是这么干的——反思"我是不是在循环？有没有进展？"）

```python
class AgentState(MessagesState):
    next: str
    count: int
    last_worker: str        # 上次派的 worker
    repeat_count: int       # 连续同一 worker 的次数

def supervisor(state: AgentState):
    count = state.get('count', 0) + 1
    if count > 10:
        return {'next': 'FINISH', 'count': count}

    next_worker = llm.with_structured_output(Router, method="function_calling") \
                     .invoke(messages)['next']

    last = state.get('last_worker', '')
    repeat = state.get('repeat_count', 0) + 1 if next_worker == last else 1

    if repeat >= 3:         # 连续 3 次同一 worker → 卡死
        return {'next': 'FINISH', 'count': count,
                'last_worker': next_worker, 'repeat_count': repeat}

    return {'next': next_worker, 'count': count,
            'last_worker': next_worker, 'repeat_count': repeat}
```

另一种卡死信号：**消息数不增长**——记 `len(state['messages'])`，连续两步一样就说明没有 worker 在产出。

---

### ④ 单 worker 限次

限制**每一个** worker 最多被调几次，防止在几个 worker 之间来回踢皮球。

```python
class AgentState(MessagesState):
    next: str
    count: int
    worker_calls: dict      # {'chat': 2, 'coder': 1, ...}

def supervisor(state: AgentState):
    count = state.get('count', 0) + 1
    if count > 10:
        return {'next': 'FINISH', 'count': count}

    next_worker = llm.with_structured_output(Router, method="function_calling") \
                     .invoke(messages)['next']

    calls = dict(state.get('worker_calls', {}))
    calls[next_worker] = calls.get(next_worker, 0) + 1

    if calls[next_worker] > 3:        # 单个 worker 最多 3 次
        return {'next': 'FINISH', 'count': count, 'worker_calls': calls}

    return {'next': next_worker, 'count': count, 'worker_calls': calls}
```

---

### ⑤ 资源预算（token / 消息数）

防止上下文无限膨胀。

```python
class AgentState(MessagesState):
    next: str
    count: int

MAX_MESSAGES = 20     # 最多 20 条消息

def supervisor(state: AgentState):
    count = state.get('count', 0) + 1

    if len(state['messages']) >= MAX_MESSAGES:   # 消息数超限
        return {'next': 'FINISH', 'count': count}
    if count > 10:
        return {'next': 'FINISH', 'count': count}
    ...
```

精确点就按 token 估：`sum(len(str(m.content)) for m in state['messages'])` 做粗略估算，或接入 tokenizer。

---

### ⑥ 人工兜底（human-in-the-loop）

超限后**不是直接 FINISH，而是 `interrupt()` 停下来问人**。

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

def supervisor(state: AgentState):
    count = state.get('count', 0) + 1

    if count > 10:
        decision = interrupt({
            "question": "已尝试 10 轮仍未解决，继续还是放弃？",
            "options": ["继续", "放弃"]
        })
        if decision == "放弃":
            return {'next': 'FINISH', 'count': count}
        else:
            return {'next': state['next'], 'count': 0}   # 重置计数，继续
    ...
```

关键点：
- 必须 `compile(checkpointer=MemorySaver())`，`interrupt()` 才能停。
- 恢复时用 `graph.invoke(Command(resume="继续"), config=config)`。

---

## 生产级组合（② + ③ + ④ + ⑥）

实际项目里通常把这几层叠在一起：

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

class AgentState(MessagesState):
    next: str
    count: int
    last_worker: str
    repeat_count: int
    worker_calls: dict

MAX_ROUNDS = 10        # ② 步数预算
MAX_REPEAT = 3         # ③ 连续同一 worker 上限
MAX_PER_WORKER = 4     # ④ 单 worker 上限

def supervisor(state: AgentState):
    count = state.get('count', 0) + 1

    # ② 步数兜底
    if count > MAX_ROUNDS:
        return ask_human(state, count)

    next_worker = llm.with_structured_output(Router, method="function_calling") \
                     .invoke(messages)['next']

    # ③ 卡死检测
    last = state.get('last_worker', '')
    repeat = state.get('repeat_count', 0) + 1 if next_worker == last else 1
    if repeat >= MAX_REPEAT:
        return ask_human(state, count)

    # ④ 单 worker 限次
    calls = dict(state.get('worker_calls', {}))
    calls[next_worker] = calls.get(next_worker, 0) + 1
    if calls[next_worker] > MAX_PER_WORKER:
        return ask_human(state, count)

    return {'next': next_worker, 'count': count,
            'last_worker': next_worker, 'repeat_count': repeat,
            'worker_calls': calls}

def ask_human(state, count):
    decision = interrupt({
        "question": "多轮仍未解决，继续还是放弃？",
        "options": ["继续", "放弃"]
    })
    if decision == "放弃":
        return {'next': 'FINISH', 'count': count}
    return {'next': state['next'], 'count': 0,
            'last_worker': '', 'repeat_count': 0, 'worker_calls': {}}
```

编译时记得带 checkpointer：

```python
graph = builder.compile(checkpointer=MemorySaver())
```

---

## 速查表

| 层级 | 做法 | 特点 | 学习建议 |
|---|---|---|---|
| ① | `recursion_limit` | 内置硬限制，最后防线 | 永远加 |
| ② | count 步数预算 | 显式「最多 N 轮」 | 必掌握 |
| ③ | 卡死检测 | 连续同一 worker / 消息不增长就提前停 | 必掌握 |
| ④ | 单 worker 限次 | 防止踢皮球 | 上生产再加 |
| ⑤ | 资源预算 | token / 消息数上限 | 上生产再加 |
| ⑥ | 人工兜底 | interrupt 停下来问人 | 上生产再加 |

**一句话总结**：学习阶段掌握 **①②③** 就够了；上生产再加 **④⑤⑥**。
