from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from pydantic import BaseModel,Field

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

class SearchQuery(BaseModel):
    """the query to fetch real time infor"""
    query:str=Field(description="the query to fetch real time infor")

class WeatherInfo(BaseModel):
    """the location to get the weather"""
    location:str=Field(description="the location to get the weather")

class UserInfo(BaseModel):
    """Extracted user information, such as name,age,email,phone if relevant"""
    name:str=Field(description="name of the user")
    age:Optional[int]=Field(description="age of the user")
    email:str=Field(description="email of the user")
    phone:Optional[str]=Field(description="phone of the user")

@tool(args_schema=SearchQuery)
def fetch_real_time_info(query):
    """fetch real time info from internet"""
    print("--------------")
    
    return "小米汽车就是好，九八九八不得了"

@tool(args_schema=WeatherInfo)
def get_weather(location):
    """get the weather of the location"""
    if location.lower() == '北京':
        return "北京的温度是20度，天气良好"
    elif location.lower()=='上海':
        return "上海的温度是30度，天气多云"
    else:
        return "未查询到天气信息"

@tool(args_schema=UserInfo)
def insert_db(name,age,email,phone):
    """based on the input parameters, insert the user info into db"""
    try:
        user=User(name=name,age=age,email=email,phone=phone)  # ✅ User 是 SQLAlchemy ORM 模型，非 Pydantic UserInfo
        session.add(user)
        session.commit()
        return "用户信息成功存储到mysql中"
    except Exception as e:
        session.rollback()
        return f"插入失败，错误是{e}"
    finally:
        session.close()
        
tools=[fetch_real_time_info,get_weather,insert_db]

from typing import TypedDict
from typing_extensions import Annotated, List, Any
from langchain_core.messages import AnyMessage,ToolMessage,SystemMessage,HumanMessage
import operator

def chat_with_model(state):
    """chat with llm"""
    print("----------------")
    messages=state["messages"]
    response=llm.invoke(messages)
    return {"messages":[response]}

class AgentState(TypedDict):
    messages:Annotated[List[AnyMessage],operator.add]

# 关键方法，自定义工具调用，不用ToolNode
def execute_function(state:AgentState):
    tool_calls=state["messages"][-1].tool_calls
    results=[]
    tools_dict={t.name:t for t in tools}  # ✅ 字典改名，避免遮蔽全局 tools
    for t in tool_calls:  # ✅ 迭代 tool_calls，而非 tools_dict
        if not t['name'] in tools_dict:
            result= "bad tool name,retry"
        else:
            result=tools_dict[t['name']].invoke(t['args'])
        results.append(ToolMessage(tool_call_id=t['id'],name=t['name'],content=str(result)))
    print('results',results)
    return {"messages":results}

def final_answer(state):
    """generate natural language responses"""
    messages=state["messages"][-1]
    return {"messages":[messages]}

SYSTEM_PROMPT="""
please summarize the information obtained so far and generate a professional response.Note,please reply in Chinese
"""

def natural_response(state):
    """generate final language response"""
    messages=state["messages"][-1]
    messages=[SystemMessage(content=SYSTEM_PROMPT)]+[HumanMessage(content=messages.content)]
    response=llm.invoke(messages)
    return {"messages":[response]}


def exists_function_calling(state:AgentState):
    result=state['messages'][-1]
    return len(result.tool_calls)>0

from IPython.display import Image,display
from langgraph.graph import StateGraph,START,END

graph=StateGraph(AgentState)

graph.add_node("chat_with_model",chat_with_model)
graph.add_node("execute_function",execute_function)
graph.add_node("final_answer",final_answer)
graph.add_node("natural_response",natural_response)

graph.add_edge(START,"chat_with_model")

graph.add_conditional_edges("chat_with_model",exists_function_calling,{
    True: "execute_function",
    False: "final_answer"
})

graph.add_edge("execute_function","natural_response")
graph.add_edge("final_answer","natural_response")

graph.add_edge("natural_response",END)

graph=graph.compile()
display(Image(graph.get_graph(xray=True).draw_mermaid_png()))

tools=[insert_db,fetch_real_time_info,get_weather]
llm=llm.bind_tools(tools)

messages=[HumanMessage(content="你好，请你介绍一下你自己")]
result1=graph.invoke({"messages":messages})

print('result1',result1["messages"][-1].content,'\n\n')

messages=[HumanMessage(content="小米汽车")]
result2=graph.invoke({"messages":messages})

print('result2',result2["messages"][-1],'\n\n')


messages=[HumanMessage(content="我是奥特曼b，今年38岁，邮箱是aoteman#qq.com,电话是12321312312")]

result3=graph.invoke({"messages":messages})
print('result3',result3["messages"][-1],'\n\n')

