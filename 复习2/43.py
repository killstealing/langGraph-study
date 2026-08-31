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

from typing import Annotated, TypedDict
import uuid
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from langgraph.graph import START, MessagesState, StateGraph, add_messages,END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig

memory=MemorySaver()
in_memory_store=InMemoryStore()

class AgentState(TypedDict):
    user_input:str
    model_response:str
    user_approval:str
    
def call_model(state):
    print("call_model start")
    messages=state['user_input']
    if '删除' in messages:
        state['user_approval']=f"用户输入的指令是:{messages}, 请人工确认是否执行"
    else:
        result=llm.invoke(messages)
        state['model_response']=result
        state['user_approval']="直接执行"
    print("call_model end")    
    return state

def execute_function(state):
    print('execute_function start')
    approval=state['user_approval']
    if approval == '是':
        response="你的删除请求已批准"
        return {'model_response':AIMessage(content=response)}
    elif approval == '否':
        response="你的删除请求已拒绝"
        return {'model_response':AIMessage(content=response)}
    else:
        return state
    
def translate_to(state):
    print('transalate to start')
    messages=state['model_response']
    system_prompt="将消息翻译成英文"
    result=llm.invoke([SystemMessage(content=system_prompt)]+[HumanMessage(
        content=messages.content
    )])
    return {'model_response':result}

builder=StateGraph(AgentState)
builder.add_node('call_model',call_model)
builder.add_node('execute_function',execute_function)
builder.add_node('translate_to',translate_to)

builder.add_edge(START,'call_model')
builder.add_edge('call_model','execute_function')
builder.add_edge('execute_function','translate_to')
builder.add_edge('translate_to',END)

graph=builder.compile(checkpointer=memory, interrupt_before=['execute_function'])

    
async def main1():
    
    config={'configurable':{'thread_id':"3"}}
    print("\n\n config",config,"******************************************************************")        

    async for event in graph.astream_events({'user_input':"我将在数据库中删除id为xigualaosi的所有信息"},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
            
    snapshot=graph.get_state(config)
    print("\n\n snapshot before",snapshot,"******************************************************************")        

    snapshot.values['user_approval']='是'
    graph.update_state(config,snapshot.values)

    snapshot=graph.get_state(config)
    print("\n\n snapshot after",snapshot,"******************************************************************")        

    async for chunk in graph.astream(None,config,stream_mode="values"):
        print(chunk)
        
    config={'configurable':{'thread_id':"3"}}
    print("\n\n config",config,"******************************************************************")        

    async for event in graph.astream_events({'user_input':"我将在数据库中删除id为xigualaosi的所有信息"},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
            
    snapshot=graph.get_state(config)
    print("\n\n snapshot before",snapshot,"******************************************************************")        

    snapshot.values['user_approval']='否'
    graph.update_state(config,snapshot.values)

    snapshot=graph.get_state(config)
    print("\n\n snapshot before",snapshot,"******************************************************************")        

    async for chunk in graph.astream(None,config,stream_mode="values"):
        print(chunk)
        
    config={'configurable':{'thread_id':"3"}}
    print("\n\n config",config,"******************************************************************")        

    async for event in graph.astream_events({'user_input':["你好，介绍一下你自己"]},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
            
    async for chunk in graph.astream(None, config, stream_mode="values"):
        print(chunk)

asyncio.run(main1())