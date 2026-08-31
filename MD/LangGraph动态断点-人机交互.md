# LangGraph 动态断点（Human-in-the-loop）

## 一、两种断点对比

| | 静态断点 | 动态断点 |
|---|---|---|
| 写法 | `compile(interrupt_before/after=[...])` | 节点内部调 `interrupt()` |
| 触发时机 | 编译时写死，每次到该节点都停 | 运行时靠代码判断，想停才停 |
| 带数据出来 | ❌ | ✅（把问题/选项带出来） |
| 恢复 | `stream(None)` / `Command(resume=...)` | `Command(resume=...)` |

## 二、动态断点怎么加：节点内用 `interrupt()`

```python
from langgraph.types import interrupt, Command

def execute_risk_function_dynamic(state):
    last_message = state['messages'][-1]
    city = last_message.tool_calls[0]['args'].get('city_name', '未知城市')

    # ① 动态断点：停在这里，把问题带出去；返回值 = 恢复时 resume 传入的值
    decision = interrupt({
        "question": f"是否允许删除 {city} 的天气数据？",
        "options": ["允许", "拒绝"]
    })

    # ② 恢复后，decision 就是用户通过 Command(resume=...) 传回来的答案
    if decision == "允许":
        result = tool_node.invoke({"messages": [last_message]})
        return result
    else:
        tool_call_id = last_message.tool_calls[0]['id']
        return {"messages": [{
            "role": "tool",
            "content": "管理员不允许执行该操作",
            "name": "delete_weather_from_db",
            "tool_call_id": tool_call_id
        }]}
```

注意：`compile()` **不写** `interrupt_before`，断点由节点内部的 `interrupt()` 动态触发。

## 三、动态断点怎么用：`Command(resume=...)` 恢复

```python
config = {"configurable": {"thread_id": "123"}}

# 1) 发起，跑到 interrupt() 自动停
for chunk in graph.stream({"messages": ["帮我删除大连的天气数据"]},
                          config=config, stream_mode="values"):
    chunk['messages'][-1].pretty_print()

# 2) 检测断点
state = graph.get_state(config)
print("next =", state.next)                              # -> ('execute_risk_function',)
print("payload =", state.tasks[0].interrupts[0].value)   # -> {'question': ..., 'options': [...]}

# 3) 恢复：把决定传回节点里的 decision
graph.invoke(Command(resume="允许"), config=config)   # 或 resume="拒绝"
```

## 四、检测断点的关键字段

- `graph.get_state(config).next` —— 非空说明停住了，返回接下来要运行的节点
- `graph.get_state(config).tasks[0].interrupts[0].value` —— `interrupt()` 带出来的 payload（**dict**）

## 五、多轮对话完整写法（run_multi_round_dialog）

推荐把"启动"和"检查断点 + 恢复"拆开，是/否统一走 `Command(resume=...)`：

```python
def run_multi_round_dialog(graph, config):
    while True:
        user_input = input("请输入你的问题，输入退出结束对话：")
        if user_input == '退出':
            print("对话已结束")
            break

        # 1) 启动这一轮：跑到 interrupt() 自动停
        graph.invoke({"messages": [user_input]}, config=config)

        # 2) 循环：有断点就询问并恢复，直到跑完
        while True:
            state = graph.get_state(config)

            if not state.tasks:                       # 跑完了，打印最终回复
                state.values["messages"][-1].pretty_print()
                break

            if not state.tasks[0].interrupts:         # 有 pending 但没 interrupt
                break

            payload = state.tasks[0].interrupts[0].value
            while True:
                ans = input(payload["question"])
                if ans in payload["options"]:         # 用 payload 里的选项，别硬编码
                    break
                print(f"输入错误，请输入 {payload['options']}")

            # 是/否统一交给节点内部处理，不再单独写 update_state
            graph.invoke(Command(resume=ans), config=config)
```

## 六、`graph.stream()` 是惰性生成器，`invoke` 更简洁

- `graph.stream(...)` 返回的是**惰性生成器**，只调用不迭代，图**不会执行**。
- 想"跑到断点/结束就停"，用 `graph.invoke(...)` 更干净：

```python
graph.invoke({"messages": [user_input]}, config=config)   # 同步跑到结束或 interrupt 停下
```

- 只有想**边跑边看中间过程**（流式打印、逐字输出）才需要 `for ... in stream()`。

## 七、常见坑

1. **选项硬编码**：`if user_input in ['是','否']` 应改成 `if ans in payload['options']`。
2. **'否' 分支别混用静态写法**：动态断点里，是/否都应该 `Command(resume=ans)`，不要用 `update_state(as_node=...)` + `stream(None)`（那是静态断点的恢复方式，会绕过节点内部的 else 分支）。
3. **`state.tasks[0].interrupts[0].value` 是 dict**，用 `['question']` 取值，不是 `.question`。

## 八、什么时候用静态断点

- **调试**：`interrupt_before=[所有节点]`，单步跑看状态。
- **步骤间人工审核**：`interrupt_after=['生成大纲']`，人看一眼再继续。
- **改状态后再继续**：边界停住，改 state，再恢复（时间旅行/fork）。

> 记忆：**在节点内部、要把问题和答案传进传出 → `interrupt()`（动态）；只在节点边界停下来看一眼/改状态 → `interrupt_before/after`（静态）。**
