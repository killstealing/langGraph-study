from langchain_core.messages import AIMessage
import json
import re
from typing import List
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

def extract_json(message: AIMessage) -> List[dict]:
    """从 AIMessage 中提取 JSON，支持两种格式：
    1. ```json ... ``` 代码块包裹
    2. 纯 JSON 文本
    """
    text = message.content
    pattern = r"```json(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    if matches:
        return [json.loads(m.strip()) for m in matches]

    # ✅ 没有 ```json 标记，尝试直接解析纯 JSON
    try:
        return [json.loads(text.strip())]
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse: {message}")
    
from langchain_core.prompts import ChatPromptTemplate

prompt=ChatPromptTemplate.from_messages(
    [
        ("system","Answer the user query. Wrap the output in `json`"),
        ("human","{query}")
    ]
)

chain=prompt | llm | extract_json
ans=chain.invoke({"query":"我叫奥特曼，今年38岁，邮箱地址是aoteman@qq.com,电话是123123123"})

print(ans)

ans=chain.invoke({"query":"你好，请介绍一下你自己"})

print(ans)