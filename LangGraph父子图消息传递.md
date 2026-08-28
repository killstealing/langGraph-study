# LangGraph 父子图消息传递（state 映射）

## 一、核心规则

**父子图之间传状态，靠"字段名对齐"——同名 key 才会自动流转，不同名需要显式映射。**

## 二、常见报错：子图拿到空 state

典型场景：

```python
class ParentState(TypedDict):      # 父图
    parent_input: str
    parent_answer: str

class SubState(TypedDict):         # 子图
    sub_input: str
    summary_answer: str
    score: str

def subgraph_node1(state):
    answer = state['sub_input']    # ❌ 拿不到，是空的
```

**原因**：父图 state 是 `{parent_input, parent_answer}`，子图 state 是 `{sub_input, summary_answer, score}`，两边 key **完全没有交集**。子图按自己的 schema 去父图状态里找 `sub_input`，父图里根本没有这个 key，所以拿到空（None）。

## 三、"桥接节点"为什么没生效

很多人会加一个中间节点试图转字段：

```python
def parent_node_start(state):
    return {'sub_input': state['parent_answer']}   # 想转字段
```

但它被加进了**父图**（父图 schema 是 `ParentState`），返回的 `sub_input` 不是父图合法字段，所以转换根本没写进状态，子图照样拿不到。**桥接节点白写了。**

## 四、修复方法

### 方案一：让父子图共用字段名（最简单，推荐）

把子图字段改成和父图对齐，桥接节点可以删掉：

```python
class SubState(TypedDict):
    parent_answer: str        # ← 跟父图字段对齐，直接共享
    summary_answer: str
    score: str

def subgraph_node1(state):
    answer = state['parent_answer']     # 直接读父图的字段
    ...
```

### 方案二：显式映射（老版本 / 复杂场景）

老版本 LangGraph（0.2.x）用 `add_node(..., input=..., output=...)`：

```python
parent_builder.add_node(
    'subgraph', subgraph,
    input={'sub_input': 'parent_answer'},   # 父图 parent_answer → 子图 sub_input
    output={'score': 'parent_score'}        # 子图 score → 父图 parent_score
)
```

⚠️ **注意**：LangGraph 1.x 已经**移除了** `add_node` 的 `input`/`output` 参数（现在签名里是 `input_schema`，`**kwargs` 是空）。所以别去抄老教程的 `input=...` 写法，用 `Command` 显式传状态或共享字段名。

## 五、关键点

1. **同名 key 自动流转**：父子图都叫 `parent_answer`，就直接共享，不用任何映射。
2. **不同名必须显式映射**：否则子图拿空 state。
3. **桥接节点要放在对的地方**：想转字段，要么改 schema 对齐，要么用映射/Command，别在父图里返回子图字段。

## 六、相关：节点函数里的消息类型坑

父子图传数据时，如果 state 字段存的是 `AIMessage` 对象，下游再用 `HumanMessage(content=aimessage)` 会报 Pydantic 校验错误，要取 `.content` 或直接传消息对象（详见《LangGraph消息与LLM调用基础.md》）。
