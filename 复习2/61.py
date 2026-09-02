import pymilvus
print(pymilvus.__version__)  # 应该输出 2.5.18
from langchain_core.prompts import PromptTemplate
from langchain.messages import HumanMessage


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

from langgraph.graph import StateGraph,MessagesState ,START,END

class AgentState(MessagesState):
    next:str
    
# 打开文件，并赋予读取模式
with open("./company.txt",'r',encoding='utf-8') as file:
    content=file.read()
    print(content)
    
from langchain_core.documents import Document
documents=[Document(page_content=content)]

# 使用向量数据库
from langchain_text_splitters import RecursiveCharacterTextSplitter

chunk_size=250
chunk_overlap=30
text_splitter=RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,chunk_overlap=chunk_overlap
)

splits=text_splitter.split_documents(documents)
print('splits',splits,'\n\n')

from langchain_ollama import OllamaEmbeddings

# DeepSeek 没有 Embedding API（/v1/embeddings 不存在，404）
# 改用本地 Ollama 的 bge-m3 模型 —— 支持中英双语，1024维向量
embeddings = OllamaEmbeddings(
    model="bge-m3",
    base_url="http://localhost:11434"
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_milvus import Milvus
# 将切割好的数据，插入到数据库中
vectorstore = Milvus.from_documents(
    documents=splits,
    collection_name="company_rag_milvus",
    embedding=embeddings,
    drop_old=True,   # ← 关键！删除之前错误 schema 的旧 collection
    connection_args={
        "uri": os.getenv("zilliz_url"),
        "token": f"{os.getenv('zilliz_User')}:{os.getenv('zilliz_Password')}",
    }
)


from langchain_core.output_parsers import StrOutputParser

prompt=PromptTemplate(
    template="""
        you are an assistant for question-answering tasks.
        use the following pieces of retrieved context to answer the question. If you don't know the answer, just 
        use three sentences maximum and keep the answer concise:
        Question: {question}
        Context: {context}
        Answer:
    """,
    input_variables={"question",'context'}
)

rag_chain=prompt | llm | StrOutputParser()

question="我的知识库中都有哪些公司信息"
retriever=vectorstore.as_retriever(search_kwargs={"k":1})

docs=retriever.invoke("question")
print('docs',docs,'\n\n')

generation=rag_chain.invoke({"context":docs,"question":question})
print('generation',generation,'\n\n')
def vec_kg(state:AgentState):
    
    messages=state["messages"][-1]
    question=messages.content
    
    prompt=PromptTemplate(
        template="""
            you are an assistant for question-answering tasks.
            use the following pieces of retrieved context to answer the question. If you don't know the answer, just 
            use three sentences maximum and keep the answer concise:
            Question: {question}
            Context: {context}
            Answer:
        """,
        input_variables={"question",'context'}
    )
    
    rag_chain=prompt | llm | StrOutputParser()
    retriever=vectorstore.as_retriever(search_kwargs={"k":1})
    docs=retriever.invoke("question")
    generation=rag_chain.invoke({"context":docs,"question":question})
    final_response=[HumanMessage(content=generation,name="vec_kg")]
    return {"messages":final_response}
    