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

from langchain_core.prompts import ChatPromptTemplate

prompt=ChatPromptTemplate.from_messages(
    [
        ("system","Answer the user query,Wrap the output in `json`"),
        ("human","{query}")
    ]
)
chain=prompt | llm
ans=chain.invoke({"query":"我叫奥特曼，今年38岁，邮箱地址是aoteman@qq.com,电话是123123123"})

print(ans.content)

ans=chain.invoke({"query":"你好，请介绍一下你自己"})
print(ans.content)