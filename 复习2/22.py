from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import requests
import json
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime
from langgraph._internal._constants import CONF, CONFIG_KEY_RUNTIME


load_dotenv()
llm=ChatOpenAI(model="deepseek-chat",
               api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",  # DeepSeek API 地址
               temperature=0
               )

from langchain_core.tools import tool

@tool
def fetch_real_time_info(query):
    """get real-time Internet information"""
    print("query:"+query)
    return {'messages':['小米汽车就是好，九八九八不得了']}

from langgraph.prebuilt import ToolNode


# 定义好工具方法，加上tool注解
@tool
def get_weather(location):
    """call to get the current weather."""
    if location.lower() in ["北京"]:
        return "北京的温度是16度，天气晴朗。"
    elif location.lower() in ["上海"]:
        return "上海的温度是30度，天气多云"
    else:
        return "不好意思，并未查询到具体的天气信息"
    
config = {CONF: {CONFIG_KEY_RUNTIME: Runtime()}}

# 将工具加入到数组中
tools=[fetch_real_time_info,get_weather]
tool_node=ToolNode(tools)

# 大模型绑定工具
model_with_tools=llm.bind_tools(tools)

# 绑定工具的大模型接受用户消息，找到要调用的工具
result1=model_with_tools.invoke("北京天气")
print('result1',result1)

# 用tool_node 执行工具调用生成结果
final_result1=tool_node.invoke({"messages":[result1]},config)
print('final_result1',final_result1)


result2=model_with_tools.invoke("小米汽车")
print('result2',result2)
final_result2=tool_node.invoke({"messages":[result2]},config)

print('final_result2',final_result2)

# 这是一个找不到工具的例子，那result3中的tool_calls是空
result3=model_with_tools.invoke("你好，介绍一下你自己")
print('result3',result3)
final_result3=tool_node.invoke({"messages":[result3]},config)

print('final_result3',final_result3)