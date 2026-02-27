"""Local RAG API using FastAPI."""
import os   
from rag_agent import retrieve_answer
from index import ingest_pdf
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="local RAG API")

upload_dir = "uploads"
os.makedirs(upload_dir, exist_ok=True)

class ChatRequest(BaseModel):
    query: str

@app.get("/")
def root():
    return {"message": "Welcome to the local RAG API!"}

@app.post("/chat")
#convert to async function
async def chat(request: ChatRequest):
    try:
        logger.info("Query received: %s", request.query)
        answer = retrieve_answer(request.query)
        return {"answer": answer}
    except Exception as e:
        logger.info("Error processing query: %s", str(e))
        return {"error": "An error occurred while processing your query."}
# def chat(request: ChatRequest):
#     try:
#         logger.info("Query received: %s", request.query)
#         answer = retrieve_answer(request.query)
#         return {"answer": answer}
#     except Exception as e:
#         logger.info("Error processing query: %s", str(e))
#         return {"error": "An error occurred while processing your query."}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        file_location = os.path.join(upload_dir, file.filename)

        if os.path.exists(file_location):
            raise HTTPException(status_code=400, detail="File already exists")

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info("File uploaded successfully: %s", file.filename)

        ingest_pdf(file_location)
        logger.info("File ingested successfully: %s", file.filename)

        return {
            "message": f"File '{file.filename}' uploaded successfully.",
            "filename": file.filename,
            "content_type": file.content_type,
            "path": file_location
        }
    except Exception as e:
        logger.error("Error uploading file: %s", str(e))
        raise HTTPException(status_code=500, detail="An error occurred while uploading the file.")


@app.get("/files")
def list_files():
    files = os.listdir(upload_dir)
    return {"files": files}

@app.delete("/files/{filename}")
def delete_file(filename: str):
    file_path = os.path.join(upload_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info("File deleted successfully: %s", filename)
        return {"message": f"File '{filename}' deleted successfully."}
    else:
        logger.warning("File not found for deletion: %s", filename)
        raise HTTPException(status_code=404, detail="File not found")