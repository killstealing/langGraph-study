# LangGraph Supervisor 多代理模式

## 一、架构

Supervisor 模式 = **一个 supervisor（编排者）+ 多个 worker（专家）+ 条件路由**：

```python
class AgentState(MessagesState):
    next: str

def supervisor(state):      # 用结构化输出决定下一个 worker
    ...
    return {'next': response['next']}

def chat(state): ...        # worker 1
def coder(state): ...       # worker 2
def sqler(state): ...       # worker 3

builder.add_edge(START, 'supervisor')
builder.add_conditional_edges('supervisor', route, {
    'chat': 'chat', 'coder': 'coder', 'sqler': 'sqler', 'FINISH': END,
})
# 每个 worker 跑完都回到 supervisor，直到 supervisor 说 FINISH
builder.add_edge('chat', 'supervisor')
builder.add_edge('coder', 'supervisor')
builder.add_edge('sqler', 'supervisor')
```

## 二、常见错误

### 1. worker 里 `llm.invoke(单消息)` 报错

```python
messages = state['messages'][-1]      # 单条消息，不是 list
result = llm.invoke(messages)         # ❌ Invalid input type
```

**修复**：传列表 `llm.invoke(state['messages'])`（详见《LangGraph消息与LLM调用基础.md》）。

### 2. "一直刷自我介绍"（死循环）

两个 bug 叠加：
- worker 只读 `state['messages'][-1]` → 第二轮读到的是自己上一轮的话，对着自己重复。
- supervisor 不 FINISH → 一直派活。

**修复**：worker 读全历史 `state['messages']` + 强化 supervisor prompt + 加兜底（见下）。

### 3. 打印两遍

用 `stream_mode="values"` 时，supervisor 只改 `next`、不加消息，但它前后 state 各输出一次，最后一条消息被重复打印。

**修复**：用 `stream_mode="updates"` 只打印新增：

```python
async for chunk in graph.astream({...}, stream_mode="updates"):
    for node_name, updates in chunk.items():
        for m in updates.get('messages', []):
            m.pretty_print()
```

或打印前去重（按 `msg.id`）。

## 三、死循环控制（重点）

**本质**：Supervisor 模式的"结束"全靠 LLM 自觉说 FINISH，LLM 解决不了就会死循环。需要**显式终止条件 + 多层兜底**。

### 六层方法

| 层级 | 做法 | 特点 |
|---|---|---|
| ① | `recursion_limit` | 内置硬限制，最后防线，永远加 |
| ② | count 步数预算 | 显式「最多 N 轮」 |
| ③ | 卡死检测 | 连续同一 worker / 消息不增长就提前停 |
| ④ | 单 worker 限次 | 防止踢皮球 |
| ⑤ | 资源预算 | token / 消息数上限 |
| ⑥ | 人工兜底 | interrupt 停下来问人 |

### ① `recursion_limit`（内置）

```python
from langgraph.errors import GraphRecursionError
try:
    graph.invoke({"messages": ["..."]}, config={"recursion_limit": 10})
except GraphRecursionError:
    print("达到最大步数")
```

### ② count 步数预算

```python
class AgentState(MessagesState):
    next: str
    count: int

def supervisor(state):
    count = state.get('count', 0) + 1
    if count > 10:
        return {'next': 'FINISH', 'count': count}
    ...
    return {'next': response['next'], 'count': count}
```

### ③ 卡死检测（stall detection，最聪明）

```python
class AgentState(MessagesState):
    next: str
    count: int
    last_worker: str
    repeat_count: int

def supervisor(state):
    count = state.get('count', 0) + 1
    if count > 10:
        return {'next': 'FINISH', 'count': count}

    next_worker = llm.with_structured_output(Router).invoke(messages)['next']
    last = state.get('last_worker', '')
    repeat = state.get('repeat_count', 0) + 1 if next_worker == last else 1
    if repeat >= 3:   # 连续 3 次同一 worker → 卡死
        return {'next': 'FINISH', 'count': count,
                'last_worker': next_worker, 'repeat_count': repeat}
    return {'next': next_worker, 'count': count,
            'last_worker': next_worker, 'repeat_count': repeat}
```

### ④ 单 worker 限次

```python
class AgentState(MessagesState):
    next: str
    count: int
    worker_calls: dict

def supervisor(state):
    next_worker = ...
    calls = dict(state.get('worker_calls', {}))
    calls[next_worker] = calls.get(next_worker, 0) + 1
    if calls[next_worker] > 3:
        return {'next': 'FINISH', 'count': count, 'worker_calls': calls}
    ...
```

### ⑤ 资源预算

```python
MAX_MESSAGES = 20
if len(state['messages']) >= MAX_MESSAGES:
    return {'next': 'FINISH', 'count': count}
```

### ⑥ 人工兜底（HITL）

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

def supervisor(state):
    count = state.get('count', 0) + 1
    if count > 10:
        decision = interrupt({"question": "多轮未解决，继续还是放弃？", "options": ["继续", "放弃"]})
        if decision == "放弃":
            return {'next': 'FINISH', 'count': count}
        return {'next': state['next'], 'count': 0}   # 重置继续
    ...
```

关键：必须 `compile(checkpointer=MemorySaver())`，恢复用 `Command(resume="继续")`。

### 生产级组合（②+③+④+⑥）

```python
class AgentState(MessagesState):
    next: str
    count: int
    last_worker: str
    repeat_count: int
    worker_calls: dict

MAX_ROUNDS = 10
MAX_REPEAT = 3
MAX_PER_WORKER = 4

def supervisor(state):
    count = state.get('count', 0) + 1
    if count > MAX_ROUNDS:
        return ask_human(state, count)

    next_worker = llm.with_structured_output(Router).invoke(messages)['next']

    last = state.get('last_worker', '')
    repeat = state.get('repeat_count', 0) + 1 if next_worker == last else 1
    if repeat >= MAX_REPEAT:
        return ask_human(state, count)

    calls = dict(state.get('worker_calls', {}))
    calls[next_worker] = calls.get(next_worker, 0) + 1
    if calls[next_worker] > MAX_PER_WORKER:
        return ask_human(state, count)

    return {'next': next_worker, 'count': count,
            'last_worker': next_worker, 'repeat_count': repeat,
            'worker_calls': calls}

def ask_human(state, count):
    decision = interrupt({"question": "多轮未解决，继续还是放弃？", "options": ["继续", "放弃"]})
    if decision == "放弃":
        return {'next': 'FINISH', 'count': count}
    return {'next': state['next'], 'count': 0,
            'last_worker': '', 'repeat_count': 0, 'worker_calls': {}}
```

## 四、一句话总结

- worker 读全历史 `state['messages']`，别读 `state['messages'][-1]`。
- 死循环控制：**学习阶段掌握 ①②③，上生产加 ④⑤⑥**。
- 打印重复：`stream_mode="updates"` 只输出增量。
