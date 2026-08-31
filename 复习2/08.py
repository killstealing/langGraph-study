from langchain_openai import ChatOpenAI
import os
# start Windows GBK 编码输出不了 emoji
import sys
sys.stdout.reconfigure(encoding='utf-8')
# end 
from dotenv import load_dotenv
from langgraph.graph import START, MessagesState, StateGraph,END
from langchain_core.messages import SystemMessage,HumanMessage

from IPython.display import display,Image
import asyncio

load_dotenv()

# 定义llm大模型
llm=ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
    temperature=0
)

# 定义节点
def chat_node(state):
    result=llm.invoke(state['messages'])
    return {'messages':result}

def action_node(state):
    system_prompt="""
    将输入的信息翻译成英文返回
    """
    result=llm.invoke([SystemMessage(content=system_prompt),
                       HumanMessage(content=state['messages'][-1].content)])
    return {'messages':result}

# 定义stateGraph
builder=StateGraph(MessagesState)

builder.add_node('chat_node',chat_node)
builder.add_node('action_node',action_node)

builder.add_edge(START,'chat_node')
builder.add_edge('chat_node','action_node')
builder.add_edge('action_node',END)

graph=builder.compile()

# 展示stateGraph
display(Image(graph.get_graph(xray=True).draw_mermaid_png()))


# 执行函数
async def main():
    async for chunk in graph.astream({"messages":['你好，介绍一下你自己']}, stream_mode="values"):
        chunk['messages'][-1].pretty_print()

asyncio.run(main())
