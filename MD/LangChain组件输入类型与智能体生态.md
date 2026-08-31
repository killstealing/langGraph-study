# LangChain/LangGraph 组件输入类型与智能体开发生态

> 核心问题：`llm`、`agent`（图）、`ToolNode` 各自 invoke 接受什么类型的输入？`PromptValue` 是什么？智能体开发还涉及哪些组件？

## 一、`llm.invoke()` 接受什么

| 输入 | 是否接受 |
|---|---|
| `str` 字符串 | ✅ |
| `PromptValue` | ✅ |
| `list[BaseMessage]` 消息列表 | ✅ |
| 单个消息对象 | ❌ `Invalid input type` |
| `dict`（如 `{'messages':[...]}`） | ❌ `Invalid input type` |

```python
llm.invoke("你好")                          # ✅
llm.invoke([HumanMessage("你好")])          # ✅
llm.invoke(HumanMessage("你好"))            # ❌ 要包成 list
llm.invoke({'messages': [...]})             # ❌ dict 是给 Chain/Tool 的
```

## 二、`agent`（`create_agent` 返回的编译图）invoke 接受什么

`create_agent` 返回的是基于 `MessagesState` 的**编译图**，输入是**状态字典**：

```python
db_agent.invoke({"messages": [HumanMessage("帮我查询销售数据")]})   # ✅ 标准：状态字典
```

- ✅ `{"messages": [...]}` —— 状态字典（标准、可靠）
- ✅ 传整个 `state`（在 graph 节点里，`state` 本身就是这个结构）
- ⚠️ 传字符串 `db_agent.invoke("...")`：**不标准**，字符串是给 `llm.invoke()` 吃的

> 一句话区分：**agent（图）吃状态字典 `{"messages":[...]}`，llm 吃字符串/列表。**

## 三、`ToolNode.invoke()` 接受什么

只接受**带 `messages` 键的状态字典**，且最后一条消息必须是**带 `tool_calls` 的 AIMessage**：

```python
tool_node = ToolNode(tools)

# 输入：{"messages": [AIMessage(tool_calls=[...])]}
result = tool_node.invoke({"messages": [aimessage_with_tool_calls]})
```

ToolNode 读最后一条 AIMessage 的 `tool_calls`，逐个执行对应工具，返回 `{"messages": [ToolMessage(...), ...]}`。

- ✅ `{"messages": [...]}`
- ❌ 不接字符串、不接单个消息

## 四、`PromptValue` 是什么

**PromptValue = "模板填完变量后、发给模型前"的中间产物**，格式中立，既能转字符串也能转消息列表。

```
PromptTemplate（模板，有 {变量}）
        │  .invoke({"变量": 值})  ← 填充变量
        ▼
   PromptValue（填好的、格式中立的 prompt）
        │  .to_string() / .to_messages()
        ▼
      llm / chat_model
```

两种实现 + 两个方法：

| 类 | 装什么 | 对应模型 |
|---|---|---|
| `StringPromptValue` | 一个字符串 | 老式字符串 LLM |
| `ChatPromptValue` | 一组消息 | 聊天模型（ChatModel） |

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是助手"),
    ("human", "{input}"),
])

pv = prompt.invoke({"input": "你好"})   # 返回 ChatPromptValue
pv.to_messages()      # [SystemMessage("你是助手"), HumanMessage("你好")]
pv.to_string()        # "System: 你是助手\nHuman: 你好"
```

`llm.invoke(prompt_value)` 内部会根据模型类型自动调 `.to_string()` 或 `.to_messages()`，所以等价于传字符串/消息列表。

## 五、智能体开发生态全景（LangGraph）

**构建 Agent 相关**
- `create_react_agent` —— 预构建的 ReAct agent，不用手写循环
- `with_structured_output()` —— 让 LLM 按指定 Schema 输出结构化数据（supervisor 里的 Router 就是）

**状态与记忆**
- `checkpointer` —— 短期记忆/持久化（`MemorySaver`、`SqliteSaver`、`PostgresSaver`）
- `Store`（`BaseStore`）—— 跨会话的长期记忆

**控制流**
- `Command` —— 显式控制（`resume`、跳转节点、并行）
- `interrupt()` —— 人机交互断点

**检索/工具增强**
- RAG —— 向量检索（向量库 + 检索器喂给 agent）
- MCP（Model Context Protocol）—— 工具集成的标准协议

**调试评估**
- `astream_events` / `stream_mode` —— 细粒度事件流
- LangSmith —— 调试、追踪、评估 agent

**多代理模式**
- Supervisor（中心化）
- Network（去中心化对等）
- Hierarchical / 父子图

## 六、速查表

| 对象 | invoke 输入 | invoke 返回 |
|---|---|---|
| `llm` | `str` / `PromptValue` / `list[消息]` | 单个 `AIMessage` |
| `model_with_tools` | 同上 | `AIMessage`（带 `tool_calls`） |
| `agent`（图） | `{"messages": [...]}` 状态字典 | `dict`：完整 state（`messages` + 其他字段） |
| `ToolNode` | `{"messages": [AIMessage(tool_calls=...)]}` | `dict`：`{"messages": [ToolMessage, ...]}` |

**核心记忆**：LLM 吃字符串/消息列表/PromptValue，返回消息；图（agent）和 ToolNode 吃状态字典 `{"messages": [...]}`，返回字典。

## 七、三者 `invoke()` 返回类型对比（含实例）

### 1. `llm.invoke()` → 单个 `AIMessage`

普通聊天模型（未绑工具）返回**一个 `AIMessage` 对象**（`BaseMessage` 子类），核心字段是 `content`：

```python
response = llm.invoke(messages)   # 返回 AIMessage
response.content                  # 文本
```

节点里 `return {"messages": [response]}`，说明 `response` 本身就是一条消息。

### 2. `model_with_tools.invoke()` → 带 `tool_calls` 的 `AIMessage`

`llm.bind_tools(tools)` 之后 `invoke`，返回**还是 `AIMessage`**，但多了 `tool_calls` 属性（列表，元素是字典）：

```python
msg = model_with_tools.invoke("北京现在多少度")   # 返回 AIMessage
msg.tool_calls
# [{'name': 'get_weather', 'args': {'location': '北京'}, 'id': 'call_00_...', 'type': 'tool_call'}]
```

> 它**不自己执行工具**，只是"声明"要调哪个工具、传什么参数，之后把这个 AIMessage 喂给 `tool_node`。

### 3. `tool_node.invoke()` → `dict`（`{"messages": [ToolMessage, ...]}`）

返回**字典**，唯一 key 是 `"messages"`，值是 `ToolMessage` 列表（一次可能多个工具调用）：

```python
result = tool_node.invoke({"messages": [aimessage_with_tool_calls]})
# {'messages': [ToolMessage(content='北京的温度是16度，天气晴朗。',
#                           name='get_weather', tool_call_id='call_00_...')]}
result["messages"][0].content   # 取工具结果字符串
```

每个 `ToolMessage` 核心字段：`content`（工具结果，字符串）、`name`（工具名）、`tool_call_id`（对应 AIMessage 里那个 tool_call 的 id）。

### 4. `agent` / `graph.invoke()` → `dict`（完整 state）

编译后的图 `invoke` 返回**图运行结束时的完整 state 字典**，不是单一消息：

```python
result = graph.invoke(input_message)
# {
#   'messages': [HumanMessage(...), AIMessage(...), AIMessage(...)],  # 完整对话历史
#   'structured_output': WeatherLoc(location='beijing')              # 自定义字段
# }
result["messages"][-1]   # 拿最后一条，才是最终回复
```

### 返回类型一句话区分

| 对象 | 返回 | 取结果方式 |
|---|---|---|
| `llm` / `model_with_tools` | `AIMessage`（单个消息） | `result.content` / `result.tool_calls` |
| `tool_node` | `dict` → `{"messages": [ToolMessage]}` | `result["messages"][0].content` |
| `graph` / `agent` | `dict` → 完整 state | `result["messages"][-1]` |

**记忆点**：LLM 返回**消息**；ToolNode 返回**装工具结果的字典**；图（agent）返回**最终状态字典**（`messages` 是完整历史，最后一条才是最终答案）。
