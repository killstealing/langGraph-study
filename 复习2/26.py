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
    注意， 中国的城市需要用对应城市的英文名称代替，例如如果要查询上海的天气，loc参数需要输入 'Shanghai'
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
from langgraph._internal._constants import CONF, CONFIG_KEY_RUNTIME
from langgraph.runtime import Runtime

config = {CONF: {CONFIG_KEY_RUNTIME: Runtime()}}

tools=[get_weather]
toolNode=ToolNode(tools)

# from langchain_classic import hub

# prompt = hub.pull("hwchase17/react")
# prompt.pretty_print()


from langsmith import Client

client = Client()
prompt = client.pull_prompt("hwchase17/react", dangerously_pull_public_prompt=True)
prompt.pretty_print()

from langchain_classic.agents import AgentExecutor,create_react_agent
from langchain_openai import ChatOpenAI

agent=create_react_agent(llm,tools,prompt)


agent_executor=AgentExecutor(agent=agent,tools=tools,verbose=True)

query1='大连今天的天气'
print('query1',query1)
result1=agent_executor.invoke({
    'input':query1
})
print('result1',result1)

query2='查一下今天大连，沈阳，天津哪个城市的气温最低'
print('query2',query2)
result2=agent_executor.invoke({
    'input':query2
})
print('result2',result2)
