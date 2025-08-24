# rag.py
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
import os

# 1. Загрузка документов
loader = DirectoryLoader("docs/", glob="**/*.*")
documents = loader.load()

# 2. Разбивка на чанки
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
texts = splitter.split_documents(documents)

# 3. Создание эмбеддингов (через Ollama)
embeddings = OllamaEmbeddings(model="llama3", base_url="http://localhost:11434")

# 4. Сохранение в векторную БД (Chroma)
db = Chroma.from_documents(texts, embeddings, persist_directory="./chroma_db")
db.persist()

# 5. Создание QA-цепочки
llm = Ollama(model="llama3", base_url="http://localhost:11434")
qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=db.as_retriever(search_kwargs={"k": 3}),
    return_source_documents=True
)

# 6. Задай вопрос
query = "Какова политика компании по отпускам?"
result = qa.invoke({"query": query})

print("Ответ:", result["result"])
print("\nИсточники:")
for doc in result["source_documents"]:
    print(f"- {doc.metadata['source']}: {doc.page_content[:200]}...")
