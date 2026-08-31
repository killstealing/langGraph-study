# LangGraph 消息与 LLM 调用基础

## 一、对象用 `.`，字典用 `[]`

Python 里两者**不通用**：

| 写法 | 靠什么 | dict | 普通类实例 | Pydantic 模型 |
|---|---|---|---|---|
| `['key']` | `__getitem__` | ✅ | ❌ | ✅ |
| `.key` | 属性 `__getattr__` | ❌ | ✅ | ✅ |

```python
d = {"question": "hi"}
d['question']   # ✅ 'hi'
d.question      # ❌ AttributeError: 'dict' object has no attribute 'question'

class Foo:
    def __init__(self):
        self.question = "hi"
f = Foo()
f.question      # ✅ 'hi'
f['question']   # ❌ TypeError: 'Foo' object is not subscriptable
```

- **字典用 `[]`**，**对象用 `.`**，只有 Pydantic 模型两头都行。
- LangGraph 里 `state.tasks[0].interrupts[0].value` 是 **dict**，所以用 `['question']`，不是 `.question`。
- 想让 `.question` 好用，就把 `interrupt()` 里传 Pydantic 模型而不是 dict（一般没必要）。

## 二、`llm.invoke()` 只接受三种输入

```python
llm.invoke("你好")                     # ✅ str
llm.invoke(prompt_value)               # ✅ PromptValue
llm.invoke([HumanMessage(...), ...])   # ✅ list of BaseMessages
```

❌ 会报 `ValueError: Invalid input type ... Must be a PromptValue, str, or list of BaseMessages`：
- 传**单个消息对象**：`llm.invoke(HumanMessage(...))` → 要包成 `[HumanMessage(...)]`
- 传 **dict**：`llm.invoke({'messages': [...]})` → dict 是给 Chain/Tool 的，不是给 invoke 的

## 三、`HumanMessage(content=...)` 的 content 不能是消息对象

```python
answer = llm.invoke(...)                       # answer 是 AIMessage 对象

# ❌ 报 Pydantic ValidationError（content 要字符串，不是消息对象）
HumanMessage(content=answer)

# ✅ 两种正确写法
llm.invoke([SystemMessage(content=sys), answer])                        # 直接传消息对象
llm.invoke([SystemMessage(content=sys), HumanMessage(content=answer.content)])  # 取文本
```

**规则**：`llm.invoke()` 的返回值要么继续当消息传，要么取 `.content` 当字符串用，别把对象塞进 `content=`。

## 四、列表拼接：`[a, b]` 和 `[a] + [b]` 没区别

```python
x = [a, b]
y = [a] + [b]
x == y          # -> True，都是 [a, b]
```

`+` 对列表就是拼接。但注意：`[SystemMessage, HumanMessage]`（**不带括号**）是**类**，不是消息实例，必须写 `[SystemMessage(content=...), HumanMessage(content=...)]`。

## 五、`messages` 返回格式：看变量本身是什么

`messages` 字段要的是**一层列表**（或单个消息）：

| `final_response` 的定义 | 正确的 return |
|---|---|
| `final_response = HumanMessage(...)`（单个对象） | `{'messages': [final_response]}` |
| `final_response = [HumanMessage(...)]`（已经是 list） | `{'messages': final_response}` |

```python
final_response = [HumanMessage(content=result.content, name="chat")]  # 已经是 list
return {'messages': final_response}    # ✅ 直接放，别再包 []
# return {'messages': [final_response]}  # ❌ 会变成 [[msg]] 嵌套列表
```

**记忆**：先想清楚变量是单个消息还是列表——单个就包 `[]`，已经是列表就直接放。
