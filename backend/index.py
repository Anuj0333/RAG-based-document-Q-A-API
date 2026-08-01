from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_openrouter import ChatOpenRouter
from sqlalchemy.orm import Session

from database.curd import save_chunk

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "rag_docs"

# client_qdrant = QdrantClient(url="http://localhost:6333")

load_dotenv()
# pdf_path = Path("documents/nodejs.pdf")

def ingest_pdf(db: Session, file_path: str,  user_id: int):
    try:
        logger.info("Starting PDF ingestion: %s", file_path)
        loader = PyPDFLoader(str(file_path))
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=200,
        )

        chunks = text_splitter.split_documents(docs)

        # Add this
        filename = Path(file_path).name

        for chunk in chunks:
            chunk.metadata.update({
                "source_file": filename,
                "user_id": user_id
            })
            # chunk.metadata["source_file"] = filename

        embedding_model = OllamaEmbeddings(model="nomic-embed-text",
                                            base_url="http://localhost:11434")
        # embedding_model = OpenAIEmbeddings(
        #     model="text-embedding-3-small",
        # )

        vector_store = QdrantVectorStore.from_documents(
            documents=chunks,
            embedding=embedding_model,
            collection_name=COLLECTION_NAME,
            url="http://localhost:6333",
        )

        for chunk in chunks:
        
            save_chunk(
                db = db,
                user_id=user_id,
                filename=filename,
                chunk_text=chunk.page_content,
                page=chunk.metadata.get("page", 0)
            )

        logger.info("Indexing complete ✅")
        return True
    except Exception as e:
        db.rollback()
        logger.error("Error ingesting PDF: %s", str(e))
        return False
    
# if __name__ == "__main__":
#     ingest_pdf("documents/nodejs.pdf")


