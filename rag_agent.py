"""RAG agent module for retrieval-augmented generation using Ollama and Qdrant."""
from dotenv import load_dotenv
# from openai import OpenAI
from langchain_ollama import OllamaEmbeddings
from ollama import Client
# from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Ollama client
client = Client(host="http://localhost:11434")
# client = OpenAI()

embedding_model = OllamaEmbeddings(model="nomic-embed-text")
# embedding_model = OpenAIEmbeddings(
#     model="text-embedding-3-small"
# )
client_qdrant = QdrantClient(url="http://localhost:6333")

vector_store = QdrantVectorStore(
    client=client_qdrant,
    embedding=embedding_model,
    collection_name="rag_docs",
)

def retrieve_context(query):
    docs = vector_store.similarity_search(query, k=3)
    return "\n\n".join([doc.page_content for doc in docs])

def retrieve_answer(user_query):
    context = retrieve_context(user_query)

    prompt = f"""
You are a helpful assistant.
Answer ONLY from the context below.

Context:
{context}

Question:
{user_query}
"""

    response = client.chat(
        model="llama3:latest",
        messages=[{"role": "user", "content": prompt}],
    )

    return response["message"]["content"]

# if __name__ == "__main__":
#     while True:
#         query = input("Ask: ")
#         print("\nAnswer:", retrieve_answer(query))