from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from pydantic import BaseModel,Field
import asyncio
from typing import Annotated, TypedDict
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from langgraph.graph import START, StateGraph, add_messages,END

load_dotenv()

llm=ChatOpenAI(model="deepseek-chat",
               base_url=os.getenv("DEEPSEEK_BASE_URL"),
               api_key=os.getenv("DEEPSEEK_API_KEY"),
               temperature=0)

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker
import pymysql  # ✅ 显式导入，让 SQLAlchemy 识别

# 创建基类
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    age = Column(Integer)
    email = Column(String(100))
    phone = Column(String(15))

# ✅ mysql:// → mysql+pymysql://，用 PyMySQL 驱动
DATABASE_URI = os.getenv("DATABASE_URI")
engine = create_engine(DATABASE_URI, echo=True)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

from typing import Optional
from langchain_core.tools import tool
import requests ,json

class WeatherLoc(BaseModel):
    location:str=Field(description="the location to get the weather")

class WeatherInfo(BaseModel):
    """Extracted weather information for a city"""
    city_id:str=Field(...,description="The unique identifier for the city")
    city_name:Optional[str]=Field(description="name of the city")
    main_weather:str=Field(description="main weather condition")
    description:Optional[str]=Field(description="a detailed description of the weather")
    temperature:Optional[str]=Field(description="current temperature of the city")
    feels_like:Optional[str]=Field(description="feels-like temperature of the city")
    temp_min:Optional[str]=Field(description="minimum temperature of the city")
    temp_max:Optional[str]=Field(description="maximum temperature of the city")

# 放在 User 类定义之后、Base.metadata.create_all(engine) 之前
class WeatherTable(Base):
    __tablename__ = 'weather'
    city_id = Column(Integer, primary_key=True)
    city_name = Column(String(100))
    main_weather = Column(String(50))
    description = Column(String(200))
    temperature = Column(String(20))
    feels_like = Column(String(20))
    temp_min = Column(String(20))
    temp_max = Column(String(20))


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

@tool(args_schema=WeatherInfo)
def insert_weather_to_db(city_id,city_name,main_weather,description,temperature,feels_like,temp_min,temp_max):
    """insert weather information into the database"""
    session=Session()
    try:
        weather=WeatherTable(city_id=city_id,city_name=city_name,main_weather=main_weather,
                        description=description,temperature=temperature,feels_like=feels_like,temp_min=temp_min,temp_max=temp_max)
        session.merge(weather)
        session.commit()
        return {"messages":[f"天气数据已成功存储到db"]}
    except Exception as e:
        session.rollback()
        return {"messages":[f"天气数据保存失败，错误是{e}"]}
    finally:
        session.close()
        
class QueryWeatherSchema(BaseModel):
    """Schema for querying weather information by city name"""
    city_name: str=Field(..., description="The name of the city to query weather information")

@tool(args_schema=QueryWeatherSchema)
def query_weather_from_db(city_name):
    """query weather information from db by city name"""
    session=Session()
    try:
        weather_data=session.query(WeatherTable).filter(WeatherTable.city_name==city_name).first()
        if weather_data:
            return {
                "city_id":weather_data.city_id,
                "city_name":weather_data.city_name,
                "main_weather":weather_data.main_weather,
                "description":weather_data.description,
                "temperature":weather_data.temperature,
                "feels_like":weather_data.feels_like,
                "temp_min":weather_data.temp_min,
                "temp_max":weather_data.temp_max
            }
        else:
            return {"messages":[f"未找到城市 {city_name} 的天气信息"]}
    except Exception as e:
        return {"messages":[f"查询失败，错误原因, {e}"]}
    finally:
        session.close()
        

from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.agents import create_agent

tools=[get_weather,insert_weather_to_db,query_weather_from_db]
with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    graph=create_agent(llm,tools=tools,checkpointer=checkpointer)
    config={'configurable':{"thread_id":'23'}}
    
    for chunk in graph.stream({"messages":["你好，我叫西瓜老师"]},config=config,stream_mode="values"):
            chunk["messages"][-1].pretty_print()
        
    for chunk in graph.stream({"messages":["请问我叫什么"]},config,stream_mode="values"):
        chunk["messages"][-1].pretty_print()

#  这里可以看看结果，这里会报错，因为SqliteSaver 已经关闭了。 那已经关闭了，可以用ExitStack来拿到之前的context
#  然后在创建agent的时候，加入到checkpointer，这样就能拿到之前的记忆了。 这段代码我先注释掉
# for chunk in graph.stream({"messages":["请问我叫什么"]},config,stream_mode="values"):
#         chunk["messages"][-1].pretty_print()
        
from contextlib import ExitStack

stack=ExitStack()
checkpointer=stack.enter_context(SqliteSaver.from_conn_string(":memory:"))
graph=create_agent(llm,tools,checkpointer=checkpointer)

# 下面代码和结果，可以看出不同的线程，记忆是分开的，
config={"configurable":{"thread_id":"33"}}

for chunk in graph.stream({"messages":['你好， 我叫西瓜老师']},config,stream_mode="values"):
    chunk['messages'][-1].pretty_print()

for chunk in graph.stream({"messages":['你好， 我是谁']},config,stream_mode="values"):
    chunk['messages'][-1].pretty_print()
    
config={"configurable":{"thread_id":"1"}}

for chunk in graph.stream({"messages":['你好， 我是谁']},config,stream_mode="values"):
    chunk['messages'][-1].pretty_print()
    
config={"configurable":{"thread_id":"1"}}

for chunk in graph.stream({"messages":['你好， 我是西瓜老师']},config,stream_mode="values"):
    chunk['messages'][-1].pretty_print()
    
config={"configurable":{"thread_id":"1"}}

for chunk in graph.stream({"messages":['你好， 我是谁']},config,stream_mode="values"):
    chunk['messages'][-1].pretty_print()
    
from contextlib import AsyncExitStack
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


async def main1():
    stack=AsyncExitStack()
    checkpointer=await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(":memory:"))

    graph=create_agent(llm,tools=tools,checkpointer=checkpointer)

    config={"configurable":{"thread_id":"211"}}

    # async for events in graph.astream_events({"messages":["帮我查一下天气"]},config=config,stream_mode="values"):
    #     if event['event']=='on_chat_model_stream':
    #         print(event['data']['chunk'].content,end="|",flush=True)

    async for chunk in graph.astream({"messages":["帮我查一下北京天气"]},config,stream_mode="values"):
        chunk['messages'][-1].pretty_print()
        
    async for chunk in graph.astream({"messages":["我刚才问了什么问题"]},config,stream_mode="values"):
        chunk["messages"][-1].pretty_print()
        
    async for events in graph.astream_events({"messages":["我刚才都问了什么问题"]},config=config,version="v2"):
        # print(events)
        if events['event']=='on_chat_model_stream':
            print(events['data']['chunk'].content,end="|",flush=True)
asyncio.run(main1())

