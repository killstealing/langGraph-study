from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI

load_dotenv()  # 加载.env文件里的变量
# print(os.getenv("DEEPSEEK_API_KEY"))  # 现在可以正常读取了

llm = ChatOpenAI(
        model="deepseek-chat",  # 使用的模型名称，目前官方推荐用 'deepseek-chat'
        api_key=os.getenv("DEEPSEEK_API_KEY"),  # 你的 DeepSeek API Key
        base_url="https://api.deepseek.com/v1",  # DeepSeek API 地址
        temperature=0,
    )

import numpy as np
import pandas as pd
import json
import io
import inspect
import requests
from langchain_core.tools import tool

@tool
def get_weather(loc):
    """
    查询即时天气函数
    :param loc: 必要参数，字符串类型，用于表示查询天气的具体城市名称
    注意， 中国的城市需要用对应城市的英文名称代替，
    :return : OpenWeather API 查询即时天气的结果，具体URL请求地址为: https://api.openweathermap.org/data/2.5/weather
    返回结果对象类型为解析之后的JSON格式对象，并用字符串形式进行表示，其中包含了全部重要的天气信息
    """
    
    url=os.getenv("WEATHER_API_URL")
    
    params={
        "q":loc,
        'appid':os.getenv('WEATHER_API_KEY'),
        'units':'metric',
        'lang':'zh_cn'
    }
    
    response=requests.get(url,params=params)
    
    data=response.json()
    return json.dumps(data)

from langgraph.prebuilt import ToolNode

tools=[get_weather]
toolNode=ToolNode(tools)

from langchain.agents import create_agent

agent = create_agent(llm, tools, system_prompt="你是一个善于调用工具来回答用户问题的助手")

result=agent.invoke({
    'messages':["大连今天的天气"]
})
print(result['messages'][-1].content)

for chunk in agent.stream({'messages':["大连今天的天气"]},stream_mode="values"):
    chunk['messages'][-1].pretty_print()
    
# result=agent.invoke({
#     'messages':["查一下今天大理，昆明和丽江哪个城市的气温最低"]
# })
# result['messages'][-1].content


for chunk in agent.stream({
    'messages':["查一下今天大理，昆明和丽江哪个城市的气温最低"]
},stream_mode="values"):
    chunk['messages'][-1].pretty_print()