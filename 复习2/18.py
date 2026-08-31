from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages

# ✅ 用 TypedDict 定义 State，避免 dict 导致的 __root__ 通道问题
class State(TypedDict):
    x: int

def node_a(state: State):
    """入口节点：x+1"""
    return {"x": state["x"] + 1}

def node_b(state: State):
    """分支B：x-2"""
    return {"x": state["x"] - 2}

def node_c(state: State):
    """分支C：x*2"""
    return {"x": state["x"] * 2}

def routing_function(state: State):
    """路由：x>=10 走 node_b，否则走 node_c"""
    if state["x"] >= 10:
        return True
    else:
        return False

builder = StateGraph(State)

builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_node("node_c", node_c)

builder.add_edge(START, "node_a")

# add_conditional_edges 的三个参数：源节点, 路由函数, {返回值: 目标节点}
builder.add_conditional_edges(
    "node_a",
    routing_function,
    {
        True: "node_b",
        False: "node_c",
    }
)

builder.add_edge("node_b", END)
builder.add_edge("node_c", END)

graph = builder.compile()

result=graph.invoke({'x':12})
print(result)