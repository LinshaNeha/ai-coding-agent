from app.core.database import SessionLocal
from app.models.code_chunk import CodeChunk
from app.services.embedder import Embedder


class Retriever:
    def __init__(self):
        self.embedder = Embedder()

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Returns the top_k most semantically similar code chunks to the query."""
        query_embedding = self.embedder.embed_text(query)

        db = SessionLocal()
        try:
            results = (
                db.query(
                    CodeChunk,
                    CodeChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .order_by(CodeChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
                .all()
            )

            return [
                {
                    "file_path": chunk.file_path,
                    "chunk_type": chunk.chunk_type,
                    "chunk_name": chunk.chunk_name,
                    "content": chunk.content,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "similarity": 1 - distance,  # cosine distance -> similarity
                }
                for chunk, distance in results
            ]
        finally:
            db.close()