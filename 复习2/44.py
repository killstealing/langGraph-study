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
from langgraph.graph import StateGraph,START,END,MessagesState
from langgraph.checkpoint.memory import MemorySaver
from IPython.display import display,Image
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
import json,requests
from langchain_core.messages import AnyMessage, SystemMessage,HumanMessage,AIMessage
from pydantic import BaseModel,Field

memory=MemorySaver()

class WeatherLoc(BaseModel):
    """the location to get the weather"""
    location:str=Field(description="the location to get the weather")

class SearchQuery(BaseModel):
    """the query to fetch real time infor"""
    query:str=Field(description="the query to fetch real time infor")
    
@tool(args_schema=SearchQuery)
def fetch_real_time_info(query):
    """fetch real time info from internet"""
    print("--------------")
    url="https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&t_weather=true"
    response=requests.get(url)
    result=json.loads(response.text)
    return result



@tool(args_schema=WeatherLoc)
def get_weather(location):
    """
    
    从 OpenWeather API 实时查询天气。仅在数据库中查询不到该城市天气时使用。
    优先使用 query_weather_from_db 工具。
    
    Function to query content weather.
    "param location: Required parameter, of type string, representing the specific city name for the weather query.
    Note that for cities in China, the corresponding English city name should be used. For example, to query the weather for Beijing,
    the location parameter should be input as 'Beijing'.
    :return: The result of the OpenWeather API query for current weather, with the specific URL request address being: https://api.openweathermap.org/data/2.5/weather.
    The return type is a JSON-formated object after parsing, represented as a string, containing all important weather information.
    
    """
    # step 1 构建请求
    url=os.getenv("WEATHER_API_URL")
    # step 2 设置查询参数
    params={
        "q":location,
        "appid":os.getenv("WEATHER_API_KEY"),
        "units":"metric",
        "lang":"zh_cn"
    }
    response=requests.get(url,params=params)
    data=response.json()
    return json.dumps(data)

tools=[get_weather,fetch_real_time_info]
tool_node=ToolNode(tools)
llm=llm.bind_tools(tools)

from typing import Annotated, Any
from langgraph.graph import add_messages


def should_continue(state):
    if state['messages'][-1].tool_calls:
        return 'function_call'
    else:
        return 'end'
    
def function_call(state):
    result=tool_node.invoke({"messages":[state['messages'][-1]]})
    return result
    
def call_model(state):
    messages=state['messages']
    result=llm.invoke(messages)
    return {"messages":[result]}

class AgentState(TypedDict):
    messages:Annotated[list[Any],add_messages]

builder=StateGraph(AgentState)

builder.add_node('call_model',call_model)
builder.add_node('function_call',function_call)

builder.add_edge(START,'call_model')
builder.add_conditional_edges('call_model',should_continue,{
    'function_call':'function_call',
    'end':END
})

builder.add_edge('function_call','call_model')
builder.add_edge('call_model',END)

graph=builder.compile(checkpointer=memory,interrupt_before=['function_call'])

async def main1():
    config={'configurable':{'thread_id':'1'}}
    print("\n\n config",config,"******************************************************************")        

    async for chunk in graph.astream({'messages':['你好，介绍一下你自己']},config=config,stream_mode="values"):
        print(chunk)
    print("\n\n config",config,"******************************************************************")        

    async for chunk in graph.astream({'messages':['你好，查询一下北京的天气']},config=config,stream_mode="values"):
        print(chunk)
        
    async for chunk in graph.astream(None,config=config,stream_mode="values"):
        chunk['messages'][-1].pretty_print()
        
asyncio.run(main1())