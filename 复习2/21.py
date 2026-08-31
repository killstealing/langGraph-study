from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI

load_dotenv()
llm=ChatOpenAI(model="deepseek-chat",
               api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",  # DeepSeek API 地址
               temperature=0
               )

from typing import Union,Optional
from pydantic import BaseModel,Field
class UserInfo(BaseModel):
    name:str=Field(description="the name of the user")
    age:Optional[int]=Field(description="the age of the user")
    email:str=Field(description="the email of the user")
    phone:Optional[str]=Field(description="the phone of the user")

class ConversationalResponse(BaseModel):
    response:str=Field(description="a conversation response to the user's query")

class FinalResponse(BaseModel):
    final_output:Union[UserInfo,ConversationalResponse]
    
structured_llm=llm.with_structured_output(FinalResponse,method="function_calling")

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

def chat_with_model(state):
    print(state)
    print("-------------------")
    messages=state["messages"]
    response=structured_llm.invoke(messages)
    return {"messages":[response]}

def final_answer(state):
    print(state)
    print("------------------")
    messages=state["messages"][-1]
    result=messages.final_output.response
    return {"messages":[result]}

def insert_db(state):
    session=Session()
    try:
        result=state["messages"][-1]
        output=result.final_output
        user=User(name=output.name,age=output.age,email=output.email,phone=output.phone)
        session.add(user)
        session.commit()
        return {"messages":[f"数据已成功存储到mysql数据库"]}
    except Exception as e:
        session.rollback()
        return {"messages":[f"数据存储失败，错误原因：{e}"]}
    finally:
        session.close()
        
from typing_extensions import TypedDict,Annotated
import operator
from langchain_core.messages import AnyMessage,HumanMessage
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage],operator.add]
    
    
def generate_branch(state:AgentState):
    result=state["messages"][-1]
    output=result.final_output

    if isinstance(output,UserInfo):
        return True
    elif isinstance(output,ConversationalResponse):
        return False
    
graph=StateGraph(AgentState)

graph.add_node("chat_with_model",chat_with_model)
graph.add_node("final_answer",final_answer)
graph.add_node("insert_db",insert_db)

graph.set_entry_point("chat_with_model")

graph.add_conditional_edges("chat_with_model",
                            generate_branch,
                            {
                                True:"insert_db",
                                False:"final_answer"
                            })

graph.set_finish_point("final_answer")
graph.set_finish_point("insert_db")

graph=graph.compile()

query="我叫奥特曼，今年38岁，邮箱地址是aoteman@qq.com,电话是123123123"
result=graph.invoke({"messages":[HumanMessage(content=query)]})

print(result)