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
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    next:str
    count:int

members=['chat','coder','sqler']
optinos=members+['FINISH']
from typing import Literal, TypedDict


class Router(TypedDict):
    """worker to route to next. If no works needed, route to FINISH"""
    next:Literal['chat','coder','sqler','FINISH']
def supervisor(state:AgentState):
    count = state.get('count', 0) + 1
    print('-------------------',count)
    # 兜底：超过最大轮数，强制结束，不再让 LLM 决定
    if count > 3:
        return {'next': 'FINISH', 'count': count}

    system_prompt="""
    "You are a supervisor tasked with managing a conversation between the "
            f" following workers: {members}. \n\n"
            "Each worker has a specific role: \n"
            "- chat: Responds directly to user inputs using natural language.\n"
            "- coder: Activated for tasks that require mathematical calculations or specific coding needs \n"
            "- sqler: Used when database queries or explicit SQL generation is needed.\n\n"
            "Given the following user request, respond with the worker to act next."
            " Each worker will perform a task and respond with their results and status."
            "When finished , respond with FINISH."
    """
    
    messages=[{'role':'system','content':system_prompt}]+state['messages']
    response=llm.with_structured_output(Router,method="function_calling").invoke(messages)
    return {'next':response['next'], 'count': count}

from langchain_core.messages import HumanMessage

def chat(state:AgentState):
    messages=state['messages']
    result=llm.invoke(messages)
    final_response=[HumanMessage(content=result.content,name="chat")]
    return {'messages':final_response}

def coder(state:AgentState):
    messages=state['messages']
    result=llm.invoke(messages)
    final_response=[HumanMessage(content=result.content,name="coder")]
    return {'messages':final_response}

def sqler(state:AgentState):
    messages=state['messages']
    result=llm.invoke(messages)
    final_response=[HumanMessage(content=result.content,name="sqler")]
    return {'messages':final_response}

def should_contine(state:AgentState):
    next=state['next']
    if next=='chat':
        return 'chat'
    elif next=='coder':
        return 'coder'
    elif next=='sqler':
        return 'sqler'
    else:
        return 'FINISH'
    
from langgraph.graph import START, StateGraph, END


builder=StateGraph(AgentState)

builder.add_node('supervisor',supervisor)
builder.add_node('chat',chat)
builder.add_node('coder',coder)
builder.add_node('sqler',sqler)

builder.add_edge(START,'supervisor')

builder.add_conditional_edges('supervisor',should_contine,{
    'chat':'chat',
    'coder':'coder',
    'sqler':'sqler',
    'FINISH':END,
})

builder.add_edge('chat','supervisor')
builder.add_edge('coder','supervisor')
builder.add_edge('sqler','supervisor')

graph=builder.compile()



async def main1():
    async for chunk in graph.astream({"messages":['帮我生成二分查找的代码，并运行一下，运行参数可以用一个简单的例子，来证明二分查找是好用的']}, stream_mode="values"):
        chunk['messages'][-1].pretty_print()
    
asyncio.run(main1())