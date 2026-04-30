import hashlib
import uuid
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings


def text_to_vector(text: str, size: int = settings.vector_size) -> list[float]:
    vector = [0.0] * size
    for token in text.casefold().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % size
        vector[index] += 1.0
    norm = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / norm for value in vector]


class HashEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [text_to_vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return text_to_vector(text)


class RagStore:
    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.qdrant_url,
            timeout=2,
            check_compatibility=False,
        )
        self.collection = settings.qdrant_collection
        self.embeddings = HashEmbeddings()

    def ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        if any(collection.name == self.collection for collection in collections):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(
                size=settings.vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def vector_store(self) -> QdrantVectorStore:
        self.ensure_collection()
        return QdrantVectorStore(
            client=self.client,
            collection_name=self.collection,
            embedding=self.embeddings,
            validate_collection_config=False,
        )

    def search(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        hits = self.vector_store().similarity_search_with_score(text, k=limit)
        return [
            {
                "score": round(score, 4),
                **document.metadata,
            }
            for document, score in hits
        ]

    def upsert_case(self, case_id: str, text: str, payload: dict[str, Any]) -> None:
        self.vector_store().add_texts(
            texts=[text],
            metadatas=[payload],
            ids=[str(uuid.uuid5(uuid.NAMESPACE_URL, case_id))],
        )
