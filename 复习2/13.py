import getpass
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

import operator
from typing import Annotated,TypedDict,List
from langgraph.graph import StateGraph, END
from IPython.display import Image, display
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph,MessagesState

from dotenv import load_dotenv
import os

load_dotenv()  # 加载.env文件里的变量

llm = ChatOpenAI(
        model="deepseek-chat",  # 使用的模型名称，目前官方推荐用 'deepseek-chat'
        api_key=os.getenv("DEEPSEEK_API_KEY"),  # 你的 DeepSeek API Key
        base_url="https://api.deepseek.com/v1",  # DeepSeek API 地址
        temperature=0,
    )

def chatbot(state:MessagesState):
    print(state)
    return {"messages":[llm.invoke(state["messages"])]}

builder=StateGraph(MessagesState)

builder.add_node("chatbot", chatbot)

builder.set_entry_point("chatbot")
builder.set_finish_point("chatbot")

graph=builder.compile()

result=graph.invoke({"messages": [("user", "你好，请你介绍一下你自己")]})
print(result)