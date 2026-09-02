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

from typing import TypedDict

class ParentState(TypedDict):
    user_input:str
    final_answer:str
    
def parent_node(state:ParentState):
    response=llm.invoke(state["user_input"])
    return {"final_answer":response}

class SubgraphState(TypedDict):
    final_answer1:str
    summary_answer:str
    score:str
    
from langchain_core.messages import AnyMessage,SystemMessage,HumanMessage,AIMessage

def subgraph_node_1(state:SubgraphState):
    system_prompt="""
    Please summary the context you receive to 50 words or less
    """
    messages=state["final_answer1"]
    messages=[SystemMessage(content=system_prompt)]+[HumanMessage(content=messages.content)]
    response=llm.invoke(messages)
    return {"summary_answer":response}
    
def subgraph_node_2(state:SubgraphState):
    messages=f"""
    This is the full content of what you received: {state["final_answer1"]} \n
    This information is summarized for the full content:{state["summary_answer"]}
    Please rate the text and summary information, returning a scale of 1 to 10. Note, only return scale value.
    """
    
    response=llm.invoke([HumanMessage(content=messages)])
    
    return {"score":response.content}

from langgraph.graph import StateGraph,START

subgraph_builder=StateGraph(SubgraphState)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_node(subgraph_node_2)
subgraph_builder.add_edge(START,"subgraph_node_1")
subgraph_builder.add_edge("subgraph_node_1","subgraph_node_2")

subgraph=subgraph_builder.compile()

def parentgraph_node2(state:ParentState):
    
    response=subgraph.invoke({"final_answer1":state["final_answer"]})
    return {"final_answer":response["score"]}

builder=StateGraph(ParentState)
builder.add_node("node_1",parent_node)
builder.add_node("node_2",parentgraph_node2)


builder.add_edge(START,"node_1")
builder.add_edge("node_1","node_2")

graph=builder.compile()

    
async def main1():
    async for chunk in graph.astream({"user_input":"我现在想学习大模型，应该关注哪些技术"},stream_mode="values"):
        print(chunk)
    
asyncio.run(main1())