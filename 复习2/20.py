from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from typing import Optional
from pydantic import BaseModel, Field
# ✅ 改用 PydanticOutputParser — 把 schema 注入 prompt，不依赖 API 原生能力
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()  # 加载.env文件里的变量
# print(os.getenv("DEEPSEEK_API_KEY"))  # 现在可以正常读取了

llm = ChatOpenAI(
        model="deepseek-chat",  # 使用的模型名称，目前官方推荐用 'deepseek-chat'
        api_key=os.getenv("DEEPSEEK_API_KEY"),  # 你的 DeepSeek API Key
        base_url="https://api.deepseek.com/v1",  # DeepSeek API 地址
        temperature=0,
    )



# ✅ TypedDict 不能用于 PydanticOutputParser，换成 BaseModel
class UserInfo(BaseModel):
    name: str = Field(description="The name of the user")
    age: Optional[int] = Field(default=None, description="The age of the user")
    email: str = Field(description="The email address of the user")
    phone: Optional[str] = Field(default=None, description="The phone number of the user")
    
# ❌ DeepSeek 不支持 with_structured_output（依赖 response_format 参数）
# structured_llm = llm.with_structured_output(UserInfo)



parser = PydanticOutputParser(pydantic_object=UserInfo)

prompt = ChatPromptTemplate.from_messages([
    ("system", "解析用户输入并提取个人信息。\n{format_instructions}"),
    ("human", "{query}"),
])

# 把 Pydantic schema 的格式化指令注入 prompt
prompt = prompt.partial(format_instructions=parser.get_format_instructions())

structured_llm = prompt | llm | parser

extracted_user_info=structured_llm.invoke("我叫奥特曼，今年38岁，邮箱地址是aoteman@qq.com,电话是123123123")

extracted_user_info
if isinstance(extracted_user_info,UserInfo):
    print("执行节点A的逻辑")
else:
    print("执行节点B的逻辑")
extracted_user_info="你好"

if isinstance(extracted_user_info,UserInfo):
    print("执行节点A的逻辑")
else:
    print("执行节点B的逻辑")

