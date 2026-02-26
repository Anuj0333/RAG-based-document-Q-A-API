"""Local RAG API using FastAPI."""
from rag_agent import retrieve_answer
from fastapi import FastAPI
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="local RAG API")

class ChatRequest(BaseModel):
    query: str

@app.get("/")
def root():
    return {"message": "Welcome to the local RAG API!"}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        logger.info("Query received: %s", request.query)
        answer = retrieve_answer(request.query)
        return {"answer": answer}
    except Exception as e:
        logger.info("Error processing query: %s", str(e))
        return {"error": "An error occurred while processing your query."}