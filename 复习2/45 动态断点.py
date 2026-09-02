import getpass
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import asyncio


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

from typing import TypedDict, Optional
from langgraph.graph import StateGraph,START,END,MessagesState
from langgraph.checkpoint.memory import MemorySaver
from IPython.display import display,Image
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
import json,requests
from langchain_core.messages import AnyMessage, SystemMessage,HumanMessage,AIMessage
from pydantic import BaseModel,Field

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

class QueryWeatherSchema(BaseModel):
    """Schema for querying weather information by city name"""
    city_name:str=Field(...,description="The name of the city to query weather information")
    
class DeleteWeatherSchema(BaseModel):
    """Schema for deleting weather information by city name"""
    city_name:str=Field(...,description="The name of the city to delete weather information")


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
        
@tool(args_schema=DeleteWeatherSchema)
def delete_weather_from_db(city_name:str):
    """Delete weather information from the database by city name"""
    session=Session()
    
    try:
        weather_data=session.query(Weather).filter(Weather.city_name==city_name).first()
        
        if weather_data:
            session.delete(weather_data)
            session.commit()
            return {"messages":[f"城市 '{city_name}' 的天气信息已成功删除"]}
        else:
            return {"messages":[f"未找到城市 '{city_name} 的天气信息'"]}
    except Exception as e:
        session.rollback()
        return {"messages":[f"删除失败，错误原因是: {e}"]}
    finally:
        session.close()


from langgraph.prebuilt import ToolNode

tools=[get_weather,query_weather_from_db,insert_weather_to_db,delete_weather_from_db]
tool_node=ToolNode(tools)

llm=llm.bind_tools(tools)

from typing import Annotated

from langgraph.graph import add_messages

memory=MemorySaver()


def call_model(state):
    messages=state['messages']
    response=llm.invoke(messages)
    return {'messages':[response]}

def should_continue(state):
    last_message=state['messages'][-1]
    if not last_message.tool_calls:
        return "end"
    elif last_message.tool_calls[0]['name'] == 'delete_weather_from_db':
        return 'execute_risk_function'
    else:
        return 'continue'
    
# def execute_normal_function(state):
#     messages=state['messages'][-1]
#     result=tool_node.invoke({"messages":[messages]})
#     return result


def execute_risk_function(state):
    messages=state['messages'][-1]
    result=tool_node.invoke({"messages":[messages]})
    return result
   
class AgentState(TypedDict):
    messages:Annotated[list[any],add_messages] 
    
from langgraph.types import interrupt, Command


def execute_risk_function_dynamic(state):
    """带动态断点的风险函数：真正执行前用 interrupt() 停下来问用户"""
    last_message = state['messages'][-1]
    city = last_message.tool_calls[0]['args'].get('city_name', '未知城市')

    # ① 动态断点：停在这里，把问题带出去；返回值 = 恢复时 Command(resume=...) 传入的值
    decision = interrupt({
        "question": f"是否允许删除 {city} 的天气数据？",
        "options": ["是", "否"]
    })

    # ② 恢复后，decision 就是用户传回来的答案
    if decision == "是":
        result = tool_node.invoke({"messages": [last_message]})
        return result
    else:
        tool_call_id = last_message.tool_calls[0]['id']
        return {"messages": [{
            "role": "tool",
            "content": "管理员不允许执行该操作",
            "name": "delete_weather_from_db",
            "tool_call_id": tool_call_id
        }]}


# 注意：这次 compile() 不写 interrupt_before，断点由节点内部的 interrupt() 动态触发
builder_dynamic = StateGraph(AgentState)
builder_dynamic.add_node('call_model', call_model)
builder_dynamic.add_node('execute_risk_function', execute_risk_function_dynamic)
builder_dynamic.add_node('execute_normal_function', tool_node)

builder_dynamic.add_edge(START, 'call_model')
builder_dynamic.add_conditional_edges('call_model', should_continue, {
    'execute_risk_function': 'execute_risk_function',
    'continue': 'execute_normal_function',
    'end': END
})
builder_dynamic.add_edge('execute_normal_function', 'call_model')
builder_dynamic.add_edge('execute_risk_function', 'call_model')
builder_dynamic.add_edge('call_model', END)

graph_dynamic = builder_dynamic.compile(checkpointer=memory)


def run_multi_round_dialog(graph,config):
    while True:
        user_input=input("请输入你的问题，输入退出结束对话")
        print(user_input)
        if user_input =='退出':
            print("对话已结束")
            break
        
        for chunk in graph.stream({"messages":[user_input]},config=config,stream_mode="values"):
            state=graph.get_state(config)
            
            if not state.tasks:
                chunk['messages'][-1].pretty_print()
                break
            if state.tasks[0].interrupts:
                while True:
                    user_input=input(state.tasks[0].interrupts[0].value['question'])
                    if user_input in ['是','否']:
                        break
                    else:
                        print("输入错误，请输入'是'或者 '否'")
                for event in graph.stream(Command(resume=user_input),config=config,stream_mode='values'):
                    event['messages'][-1].pretty_print()
                               
config ={"configurable":{"thread_id":"132"}}
run_multi_round_dialog(graph_dynamic,config)