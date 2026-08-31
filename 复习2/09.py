# start Windows GBK 编码输出不了 emoji
import sys
sys.stdout.reconfigure(encoding='utf-8')
# end 

from langgraph.graph import StateGraph
from langgraph.graph import START,END

builder=StateGraph(dict)

def addition(state):
    print(state)
    return {"x":state["x"]+1}

def subtraction(state):
    print(state)
    return {"y":state["x"]-2}


builder.add_node("addition",addition)
builder.add_node("subtraction",subtraction)

builder.add_edge(START,"addition")
builder.add_edge("addition","subtraction")
builder.add_edge("subtraction",END)

graph= builder.compile()
answer=graph.invoke({"x":10})
print(answer)
