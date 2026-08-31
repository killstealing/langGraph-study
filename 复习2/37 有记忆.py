from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from pydantic import BaseModel,Field
import asyncio

load_dotenv()

llm=ChatOpenAI(model="deepseek-chat",
               base_url=os.getenv("DEEPSEEK_BASE_URL"),
               api_key=os.getenv("DEEPSEEK_API_KEY"),
               temperature=0)

from typing import TypedDict, Annotated
from langchain.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph,START,END
from langgraph.graph.message import add_messages
from IPython.display import display,Image
from langgraph.checkpoint.memory import MemorySaver


class State(TypedDict):
    messages:Annotated[list,add_messages]
    
    
def call_model(state:State):
    response=llm.invoke(state["messages"])
    return {"messages":response}

def translate_message(state:State):
    system_prompt="""
    Please translate the text in any language into English as output
    """
    messages=state["messages"][-1]
    messages=[SystemMessage(content=system_prompt)]+ [HumanMessage(content=messages.content)]
    response=llm.invoke(messages)
    return {"messages":response}

builder=StateGraph(State)

builder.add_node("call_model",call_model)
builder.add_node("translate_message",translate_message)

builder.add_edge(START,"call_model")
builder.add_edge("call_model","translate_message")
builder.add_edge("translate_message",END)

graph=builder.compile()
memory=MemorySaver()
graph_with_memory=builder.compile(checkpointer=memory)


config={"configurable":{"thread_id":"1"}}

async def main():
    async for chunk in graph_with_memory.astream(input={"messages":["你好，我叫黄瓜"]},config=config,stream_mode="values"):
        chunk["messages"][-1].pretty_print()
        
    async for chunk in graph_with_memory.astream(input={"messages":["你好，我是谁"]},config=config,stream_mode="values"):
            chunk["messages"][-1].pretty_print()  
    
asyncio.run(main())