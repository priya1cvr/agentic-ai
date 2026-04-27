from langchain_ollama import OllamaLLM
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA

# Step 1: Local LLM
llm = OllamaLLM(model=MODEL_NAME, keep_alive=0)

#  Step 2: Sample documents (simulate logs / docs)
docs = [
    "Pipeline failed due to null values in customer_id column",
    "ETL job uses left join between orders and customers",
    "Null values cause aggregation errors in Spark",
    "Retry logic is missing in pipeline"
]

#  Step 3: Split text
text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=10)
texts = text_splitter.create_documents(docs)

# Step 4: Embeddings
embeddings = HuggingFaceEmbeddings()

#  Step 5: Vector DB
db = FAISS.from_documents(texts, embeddings)

#  Step 6: RAG Chain
qa = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=db.as_retriever()
)

#  Step 7: Query
query = "Why did the pipeline fail?"

result = qa.invoke(query)

print("\nANSWER:\n")
print(result)