from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI

load_dotenv()

llm=ChatOpenAI(model="deepseek-chat",
               base_url=os.getenv("DEEPSEEK_BASE_URL"),
               api_key=os.getenv("DEEPSEEK_API_KEY"),
               temperature=0)

from pydantic import BaseModel,Field
from langchain_core.tools import tool
import requests
import json

class SearchQuery(BaseModel):
    query:str=Field(description="questions for network queries")

@tool(args_schema=SearchQuery)
def fetch_real_time_data(query):
    """get real time data from website"""
    print("query in fetch_real_time_data:"+query)
    return '小米汽车就是好，九八九八不得了'

class WeatherInfo(BaseModel):
    location:str=Field(description="location of the weather")

@tool(args_schema=WeatherInfo)
def get_weather(location):
    """get weather based on the location"""
    if location.lower() in ['北京']:
        return "北京的温度是17度，天气良好"
    elif location.lower() == '上海':
        return "上海的温度是30度，天气多云"
    else:
        return "未查询到天气信息"
    
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
class UserInfo(BaseModel):
    name: str=Field(description="The name of the user")
    age: Optional[int]=Field(description="The age of the user")
    email:str=Field(description="The email address of the user")
    phone:Optional[str]=Field(description="The phone number of the user")

@tool(args_schema=UserInfo)
def insert_db(name,age,email,phone):
    """insert the user info into database"""
    session=Session()
    try:
        user=UserInfo(name=name,age=age,email=email,phone=phone)
        session.add(user)
        session.commit()
        return {"messages":[f"数据已成功存储到数据库中"]}
    except Exception as e:
        session.rollback()
        return {"messages":[f"数据存储失败，异常是{e}"]}
    finally:
        session.close()

from langgraph.prebuilt import ToolNode

tools=[fetch_real_time_data,get_weather,insert_db]
tool_node=ToolNode(tools)
llm_with_tools=llm.bind_tools(tools)

from typing import Union


class ConversationResponse(BaseModel):
    """A conversation response to the user's query"""
    response:str=Field(description="A conversation response to the user's query")

class FinalResponse(BaseModel):
    """Final response containing either user info or a conversational response"""
    final_output:Union[ConversationResponse,SearchQuery,WeatherInfo,UserInfo]
    

from langchain_core.messages import AIMessage,HumanMessage
def chat_with_model(state):
    """generate structured response"""
    print("Current conversation state:",state)
    print("-------------------")
    messages=state["messages"]
    responseFromAI=llm.with_structured_output(FinalResponse,method="function_calling").invoke(messages)
    return {
        "messages":[AIMessage(content=str(responseFromAI))],
        "structured_output":responseFromAI.final_output}
    
def final_response(state):
    """conversation final answer for user"""
    print("final answer current state",state)
    print("------------------")
    messages=state["messages"]
    response=llm.invoke(messages)
    return {"messages":[response]}

def execute_function(state):
    """generate natural language response"""
    print("execute function, current state",state)
    print("---------------------------")
    output=state["structured_output"]
    
    responseFromLLM=llm_with_tools.invoke(str(output))
    # print("responseFromLLM:"+responseFromLLM)
    response=tool_node.invoke({"messages":[responseFromLLM]})
    print(f"response:{response}")
    response=response["messages"][0].content
    return {"messages":[response]}


from typing import Any,List,TypedDict,Optional
from typing_extensions import Annotated
from langchain_core.messages import AnyMessage
import operator

class AgentState(TypedDict):
    messages:Annotated[List[AnyMessage],operator.add]
    structured_output:Optional[Any]
    
def generate_branch(state:AgentState):
    """route of the agent"""
    output=state["structured_output"]
    if isinstance(output, ConversationResponse):
        return False
    else:
        return True
    
from langgraph.graph import StateGraph,START,END

graph=StateGraph(AgentState)

graph.add_node("chat_with_model",chat_with_model)
graph.add_node("final_response",final_response)
graph.add_node("execute_function",execute_function)

graph.add_edge(START,"chat_with_model")
graph.add_conditional_edges("chat_with_model",generate_branch,{
    True:"execute_function",
    False: "final_response"
})
graph.set_finish_point("final_response")
graph.set_finish_point("execute_function")

graph=graph.compile()

from langchain_core.messages import AIMessage

query="你好，简单介绍一下你自己"
input_message={"messages":[HumanMessage(content=query)]}

result=graph.invoke(input_message)
print('result',result['messages'][-1].content)
print('\n\n')

query="小米汽车"
input_message={"messages":[HumanMessage(content=query)]}
result1=graph.invoke(input_message)
print('result1',result1['messages'][-1])
print('\n\n')

query="查询上海的天气，并且保存到数据库中"
input_message={"messages":[HumanMessage(content=query)]}
result2=graph.invoke(input_message)
print('result2',result2['messages'][-1])