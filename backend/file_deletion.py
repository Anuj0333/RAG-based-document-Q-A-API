from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(url="http://localhost:6333")

COLLECTION_NAME = "rag_docs"

def delete_from_qdrant(filename: str, user_id: int):
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="source_file",
                    match=MatchValue(value=filename),
                ),
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                ),
            ]
        ),
    )