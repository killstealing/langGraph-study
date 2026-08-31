# Python 类型注解：List vs list、TypedDict vs dict

LangGraph 定义 State 时经常碰到这几个写法，本质都是 Python 类型注解的问题。这里统一整理。

## 一、`List`（大写）和 `list`（小写）的区别

`List` 来自 `typing` 模块，`list` 是 Python 内置类型。两者在**注解里是同一个意思**，区别是「历史遗留」。

| | `list`（内置，小写） | `List`（typing，大写） |
|---|---|---|
| 来源 | Python 内置类型 | `from typing import List` |
| 能否带参数 | Python 3.9+ 才能 `list[str]` | 一直能 `List[str]` |
| 运行时代价 | 无 | 略有（只在注解里，无所谓） |
| 推荐度 | **3.9+ 推荐** | 兼容旧版本才用 |

**历史原因**：Python 3.9 之前，内置类型 `list` 不支持泛型，不能写 `list[str]`，只能 `from typing import List` 写 `List[str]`。3.9 之后（PEP 585）内置类型支持泛型了，官方推荐直接用**小写** `list[str]`。

```python
# 旧写法（兼容 3.9 以下）
from typing import List
class State(TypedDict):
    messages: Annotated[List[str], operator.add]

# 新写法（推荐，3.9+，少一行 import）
from typing import Annotated, TypedDict
class State(TypedDict):
    messages: Annotated[list[str], operator.add]
```

**运行时行为完全一样**，只是写法来源不同。

### 易混小坑

`List` 是**注解专用**，不能用来做运行时操作：

```python
isinstance(x, List)   # ❌ 会报错（List 不能用于 isinstance）
isinstance(x, list)   # ✅ 运行时判断用这个
```

**一句话**：`List` 和 `list` 在注解里一个意思；`List` 是旧时代为「支持泛型」造的，Python 3.9+ 直接用 `list`。

## 二、TypedDict vs 裸 dict（企业级 State 定义）

企业级项目定义 AgentState，**要提前定义好，不要直接用裸 `dict`**。

### 裸 `dict` 的问题

1. **没有类型检查** — 打错 key（`"x"` 写成 `"X"`）不报错，静默创建新 key，难排查。
2. **IDE 没有自动补全** — 靠脑子记有哪些字段。
3. **无法定义默认值和 reducer** — 并发分支更新同一字段时，合并策略（覆盖/累加/追加）没法控制，只能用默认覆盖。
4. **字段无约束、无校验** — 任何节点都能塞任意字段，state 越来越乱。
5. **不可维护** — 节点多了，没人知道 state 里到底有什么。

### 推荐写法一：`TypedDict`（最推荐，LangGraph 原生，轻量）

```python
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    x: int
    y: int                        # 普通字段，默认「后写覆盖」
    messages: Annotated[list, add]   # reducer：并发时「累加」而非覆盖

builder = StateGraph(AgentState)
```

`Annotated[类型, reducer]` 是核心：它决定**多个分支并发写同一个字段时如何合并**，这是裸 `dict` 完全做不到的。

### 推荐写法二：`Pydantic BaseModel`（需要校验/默认值时）

```python
from pydantic import BaseModel

class AgentState(BaseModel):
    x: int = 0
    y: int = 0
```

能做字段校验、给默认值、保证类型。但有坑（key 不能和内置属性重名、不能定义 `add` reducer 等），**一般场景优先 `TypedDict`**。

### 结论

- **入门/单文件练习**：`StateGraph(dict)` 能跑，没问题。
- **企业级/多节点/多分支**：用 `TypedDict` + `Annotated` 定义 reducer（官方推荐、社区主流）。
- **需要强校验、默认值、数据契约**：再上 `Pydantic`。

## 三、`Annotated` 是什么

`Annotated[类型, 元数据]` 在保留原类型的同时，给类型「贴一个额外标签」。LangGraph 用第二个参数当 **reducer**（合并函数）：

```python
from typing import Annotated
from operator import add

# messages 字段是 list，合并策略是 add（拼接，而非覆盖）
messages: Annotated[list, add]
```

- `add`：列表拼接 / 数字相加，常用于 `messages`
- 自定义函数：`Annotated[int, lambda left, right: left + right]` 也能当 reducer

**一句话**：`Annotated` 第一个参数是「类型」，第二个参数是「这个字段怎么合并」。
