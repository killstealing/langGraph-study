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
    messages:Annotated[list,add_messages]
    
def call_model(state:MessagesState,config:RunnableConfig,*,store:BaseStore):
    
    user_id=config['configurable']['user_id']
    
    namespace=('memories',user_id)
    memories = store.search(namespace)
    
    info="\n".join([d.value['data'] for d in memories])
    
    last_message=state['messages'][-1]
    
    store.put(namespace,str(uuid.uuid4()),{'data':last_message.content})
        
    system_prompt=f"Answer the user's question in context: {info}"
    result=llm.invoke([SystemMessage(content=system_prompt)]+state['messages'])
    
    store.put(namespace,str(uuid.uuid4()),{'data':result.content})
    return {'messages':[result]}


builder=StateGraph(AgentState)
builder.add_node('call_model',call_model)

builder.add_edge(START,'call_model')
builder.add_edge('call_model',END)

graph=builder.compile(checkpointer=memory,store=in_memory_store)
   
async def main1():
    config={'configurable':{'thread_id':"1"},'user_id':'1'}

    async for event in graph.astream_events({'messages':["你好，介绍一下你自己"]},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
    print("\n\n",config,"******************************************************************")        
            
    config={'configurable':{'thread_id':"1"},'user_id':'1'}

    async for event in graph.astream_events({'messages':["你好，我是西瓜老师，介绍一下你自己"]},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
    print("\n\n",config,"******************************************************************")        

    config={'configurable':{'thread_id':"1"},'user_id':'1'}

    async for event in graph.astream_events({'messages':["你好 我是谁"]},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
    print("\n\n",config,"******************************************************************")        
        
    config={'configurable':{'thread_id':"12"},'user_id':'1'}

    async for event in graph.astream_events({'messages':["你好 我是谁"]},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
    print("\n\n",config,"******************************************************************")        

    config={'configurable':{'thread_id':"12"},'user_id':'3'}

    async for event in graph.astream_events({'messages':["你好 我是谁"]},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
    print("\n\n",config,"******************************************************************")        
    
    config={'configurable':{'thread_id':"14"},'user_id':'4'}

    async for event in graph.astream_events({'messages':["你好 我是谁"]},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)
    print("\n\n",config,"******************************************************************")        
    config={'configurable':{'thread_id':"145"},'user_id':'3'}

    async for event in graph.astream_events({'messages':["你好 我是谁"]},config,stream_mode="values"):
        if event['event']=='on_chat_model_stream':
            print(event['data']['chunk'].content,end='|',flush=True)   
    print("\n\n",config,"******************************************************************")        
asyncio.run(main1())