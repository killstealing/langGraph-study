import getpass
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()
llm=ChatOpenAI(model="deepseek-chat",
               base_url=os.getenv("DEEPSEEK_BASE_URL"),
               api_key=os.getenv("DEEPSEEK_API_KEY"),
               temperature=0)

# 打开文件，并赋予读取模式
with open("./company.txt",'r',encoding='utf-8') as file:
    content=file.read()
    print(content)
    
from langchain_core.documents import Document

documents=[Document(page_content=content)]

from langchain_community.graphs import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI



graph=Neo4jGraph(url=os.getenv("NEO4J_URI"),
                 username=os.getenv("NEO4J_USERNAME"),
                 password=os.getenv("NEO4J_PASSWORD"),
                 database=os.getenv("NEO4J_DATABASE"))

# 图转换器配置
graph_transformer=LLMGraphTransformer(llm=llm,ignore_tool_usage=True,
    allowed_nodes=["公司","产品","技术","市场","活动","合作伙伴"],
    allowed_relationships=["推出","参与","合作","位于","开发"])

graph_documents=graph_transformer.convert_to_graph_documents(documents)

# 将数据插入到neo4j里面
graph.add_graph_documents(graph_documents)


print(f"Graph documents: {len(graph_documents)}")
print(f"Nodes from 1st graph doc: {graph_documents[0].nodes}")
print(f"Relationships from 1st graph doc: {graph_documents[0].relationships}")

