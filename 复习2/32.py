from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from pydantic import BaseModel,Field
import asyncio
from langchain_core.messages import HumanMessage,AIMessageChunk

load_dotenv()

llm=ChatOpenAI(model="deepseek-chat",
               base_url=os.getenv("DEEPSEEK_BASE_URL"),
               api_key=os.getenv("DEEPSEEK_API_KEY"),
               temperature=0)

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import pymysql  # ✅ 显式导入，让 SQLAlchemy 识别

# 创建基类
Base = declarative_base()

class Weather(Base):
    __tablename__ = 'weather'
    city_id = Column(Integer, primary_key=True)
    city_name = Column(String(50))
    main_weather = Column(String(50))
    description = Column(String(100))
    temperature = Column(Float)
    feels_like=Column(Float)
    temp_min=Column(Float)
    temp_max=Column(Float)

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
        weather=Weather(city_id=city_id,city_name=city_name,main_weather=main_weather,
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
        weather_data=session.query(Weather).filter(Weather.city_name==city_name).first()
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
        
class SearchQuery(BaseModel):
    """the query to fetch real time infor"""
    query: str = Field(description="the query to fetch real time infor")


@tool(args_schema=SearchQuery)
def fetch_real_time_info(query):
    """fetch real time info from internet"""
    print("--------------")
    url = os.getenv("BAIDU_API_URL")

    payload = json.dumps(
        {
            "messages": [{"role": "user", "content": query}],
            "edition": "standard",
            "search_source": "baidu_search_v2",
            "search_recency_filter": "week",
        },
        ensure_ascii=False,
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.getenv("BAIDU_API_KEY"),
    }

    response = requests.request(
        "POST", url, headers=headers, data=payload.encode("utf-8")
    )

    response.encoding = "utf-8"
    result = json.loads(response.text)
    return result

tools=[fetch_real_time_info,get_weather,insert_weather_to_db,query_weather_from_db]

from langchain.agents import create_agent

graph=create_agent(llm,tools)
graph


# 关键代码 stream_mode values, debug,updates, messages
def print_stream(stream):
    for sub_stream in stream:
        # print(sub_stream)
        message=sub_stream['messages'][-1]
        message.pretty_print()
        
input_messages={'messages':["你好，北京的天气怎么样"]}
print_stream(graph.stream(input_messages,stream_mode='values'))

def print_stream(stream):
    for sub_stream in stream:
        print(sub_stream)
        # message=sub_stream['messages'][-1]
        # message.pretty_print()
        
input_messages={'messages':["你好，北京的天气怎么样"]}
print_stream(graph.stream(input_messages,stream_mode='updates'))

def print_stream(stream):
    for sub_stream in stream:
        print(sub_stream)
        # message=sub_stream['messages'][-1]
        # message.pretty_print()
        
input_messages={'messages':["你好，北京的天气怎么样"]}
print_stream(graph.stream(input_messages,stream_mode='debug'))


        



                
# 执行函数
async def main():
    # async for chunk in graph.astream(input={'messages':['你好，北京的天气怎么样']},stream_mode="values"):
    #     chunk['messages'][-1].pretty_print()
    
    # async for chunk in graph.astream(input={'messages':['你好，北京的天气怎么样']},stream_mode="values"):
    #     final_result=chunk
    # final_result['messages'][-1].pretty_print()

    # inputs={"messages":[("human","你好，大理的天气怎么样")]}
    # async for chunk in graph.astream(inputs,stream_mode="updates"):
    #     for node,values in chunk.items():
    #         print(f"接收到的更新节点：{node}")
    #         print(values)
    #         print("\n\n")
    first=True
    async for msg,metadata in graph.astream({"messages":["你好，帮我查询一下数据库中的沈阳的天气数据"]},stream_mode="messages"):
        if msg.content and not isinstance(msg,HumanMessage):
            print(msg.content,end="|",flush=True)
            
            if isinstance(msg,AIMessageChunk):
                if first:
                    gathered=msg
                    first=False
                else:
                    gathered=gathered+msg
                    
                if msg.tool_call_chunks:
                    print(gathered.tool_calls)
        
        

asyncio.run(main())