import operator
from langgraph.graph import START,StateGraph,END
from typing import Annotated, TypedDict, List

class State(TypedDict):
    messages: Annotated[List[str],operator.add]

def addition(state):
    print(state)
    msg=state['messages'][-1]
    response={"x":msg["x"]+1}
    return {"messages":[response]}

def subtraction(state):
    print(state)
    msg=state['messages'][-1]
    response={"x":msg["x"]-2}
    return {"messages":[response]}

builder=StateGraph(State)

builder.add_node("addition",addition)
builder.add_node("subtraction",subtraction)

builder.add_edge(START,"addition")
builder.add_edge("addition","subtraction")
builder.add_edge("subtraction",END)

graph=builder.compile()

input_state={'messages':[{"x":10}]}
result=graph.invoke(input_state)
print(result)