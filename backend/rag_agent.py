"""RAG agent module for retrieval-augmented generation using Ollama and Qdrant."""
import os

from dotenv import load_dotenv
# from openai import OpenAI
from langchain_ollama import OllamaEmbeddings, ChatOllama
from ollama import Client
# from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Filter,
    FieldCondition,
    MatchValue,
)
from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from database.curd import (
    save_message,
    load_messages,
    get_chat,
    update_chat_title,
    get_chunks
)
from rank_bm25 import BM25Okapi

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("OPEN_ROUTER_API_KEY")
# print("OPEN_ROUTER_API_KEY:", api_key)

# memory = {}

# Ollama client
client = Client(host="http://localhost:11434")

bm25_cache = {}


# OpenRouter client
openrouter_client = ChatOpenRouter(
    api_key=api_key,
    model="openai/gpt-oss-20b:free",
    temperature=0,
    max_tokens=1024,
    max_retries=2,
)

# client = OpenAI()
embedding_model = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)
# embedding_model = OllamaEmbeddings(model="nomic-embed-text")
# embedding_model = OpenAIEmbeddings(
#     model="text-embedding-3-small"
# )
# url = os.getenv("QDRANT_URL")
# api_key=os.getenv("QDRANT_APIKEY")
# # print("cloud_qrdant_url:",url)
# # print("qdrant_api_key:", api_key)
# client_qdrant = QdrantClient(
#     url=url,
#     api_key=api_key,
#     cloud_inference=True
# )
client_qdrant = QdrantClient(url="http://localhost:6333")

# vector_store = QdrantVectorStore(
#     # path="./qdrant_db",
#     client=client_qdrant,
#     embedding=embedding_model,
#     collection_name="rag_docs",
# )


# ## Helper Functions
# def get_memory(session_id: str):
#     if session_id not in memory:
#         memory[session_id] = []
#     return memory[session_id]

def get_chat_history(db, session_id, user_id):

    messages = load_messages(db, session_id, user_id)

    history = []

    for msg in messages:

        if msg.role == "user":
            history.append(
                HumanMessage(content=msg.content)
            )

        else:
            history.append(
                AIMessage(content=msg.content)
            )

    return history


def get_vector_store():
    return QdrantVectorStore(
        client=client_qdrant,
        embedding=embedding_model,
        collection_name="rag_docs",
    )
 
def retrieve_context(query, user_id):
    # points, _ = client_qdrant.scroll(
    #     collection_name="rag_docs",
    #     limit=10,
    #     with_payload=True,
    # )

    # for point in points:
    #     print(point.payload)

    vector_store = get_vector_store()
    docs = vector_store.similarity_search(
        query,
        k=3,
        filter=Filter(
            must=[
                FieldCondition(
                    # key="user_id",
                    key="metadata.user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )
    )
    # for doc in docs:
    #     print(doc.metadata)
    if not docs:
        return [],"No relevant context found."
    context =  "\n\n".join([doc.page_content for doc in docs])

    return docs,context

def retrieve_answer(db, user_query, session_id, user_id):
    logger.info("User query: %s", user_query)
    # print("Session ID:", session_id)

    chunks = get_chunks(db, user_id)

    bm25_docs = []

    if chunks:
        if user_id not in bm25_cache:
            tokenized_docs = [
                chunk.chunk_text.lower().split()
                for chunk in chunks
            ]

            bm25_cache[user_id] = (
                BM25Okapi(tokenized_docs),
                chunks,
            )
        # bm25 = BM25Okapi(tokenized_docs)
        bm25, chunks = bm25_cache[user_id]

        query_tokens = user_query.lower().split()

        scores = bm25.get_scores(query_tokens)

        top_indices = [
            i
            for i in sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True
            )
            if scores[i] > 0
        ][:3]

        bm25_docs = [
            chunks[i].chunk_text
            for i in top_indices
        ]

    history = get_chat_history(db, session_id, user_id)
    # print("History length:", len(history))

    # history.append(HumanMessage(content=user_query))

    # _, vector_context = retrieve_context(user_query, user_id)

    # bm25_context = "\n\n".join(bm25_docs)
    # print("Retrieved context:", context)

    vector_docs, _ = retrieve_context(user_query, user_id)

    contexts = []

    seen = set()

    for text in bm25_docs:

        if text not in seen:
            contexts.append(text)
            seen.add(text)

    for doc in vector_docs:

        if doc.page_content not in seen:
            contexts.append(doc.page_content)
            seen.add(doc.page_content)

    context = "\n\n".join(contexts)
    if not context:
        context = "No relevant context found."

    logger.info("Retrieved context length: %d", len(context))

    prompt = f"""
        Retrieved Context
        -----------------
        {context}

        Instructions
        ------------
        1. Answer primarily using the retrieved context.
        2. Use previous conversation if relevant.
        3. If the context doesn't contain the answer, clearly say so.
        4. Do not fabricate information.

        Current Question
        ----------------
        {user_query}
    """

    messages = [

        SystemMessage(
            content="""
        You are a helpful AI assistant.
        Use conversation history when appropriate.
        """
    #         content="""
    # You are a helpful AI assistant.

    # Answer ONLY using the provided context.

    # If the answer is unavailable,
    # say you don't know.

    # Also use previous conversation whenever useful.
    # """
        )

    ]

    messages.extend(history)

    messages.append(
        HumanMessage(content=prompt)
    )
    #    prompt = f"""
    # You are a helpful assistant.
    # Answer ONLY from the context below.

    # Context:
    # {context}

    # Question:
    # {user_query}
    # """

    # response = client.chat(
    #     model="phi3",
    #     messages=[{"role": "user", "content": prompt}],
    # )

    try:
        response = openrouter_client.invoke(messages)
    except Exception as e:
        logger.exception(e)
        return "Sorry, I couldn't generate a response."

    # history.append(AIMessage(content=response.content))
    save_message(
        db,
        session_id,
        "user",
        user_query
    )

    save_message(
        db,
        session_id,
        "assistant",
        response.content
    )

    chat = get_chat(db, session_id, user_id)
    # print("Current Title:", chat.title if chat else None)

    if chat and chat.title == "New Chat":
        title_prompt = f"""
            Generate a short chat title
            (3-6 words).

            Question:

            {user_query}

            Only return the title.
        """
        title = openrouter_client.invoke(
            [
                HumanMessage(content=title_prompt)
            ]
        )

        update_chat_title(
            db,
            session_id,
            user_id,
            title.content,
        )

    return response.content
    # return response["message"]["content"]

# if __name__ == "__main__":
#     while True:
#         query = input("Ask: ")
#         print("\nAnswer:", retrieve_answer(query))