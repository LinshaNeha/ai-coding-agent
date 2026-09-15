from app.core.database import SessionLocal
from app.models.code_chunk import CodeChunk
from app.services.indexer import CodeIndexer
from app.services.embedder import Embedder


def index_codebase(directory: str, clear_existing: bool = True):
    indexer = CodeIndexer()
    embedder = Embedder()
    db = SessionLocal()

    try:
        if clear_existing:
            db.query(CodeChunk).delete()
            db.commit()
            print("Cleared existing chunks.")

        chunks = indexer.index_directory(directory)
        print(f"Found {len(chunks)} chunks. Generating embeddings...")

        for i, chunk in enumerate(chunks, 1):
            embedding = embedder.embed_text(chunk["content"])
            db_chunk = CodeChunk(
                file_path=chunk["file_path"],
                chunk_type=chunk["chunk_type"],
                chunk_name=chunk["chunk_name"],
                content=chunk["content"],
                start_line=chunk["start_line"],
                end_line=chunk["end_line"],
                embedding=embedding,
            )
            db.add(db_chunk)
            print(f"  [{i}/{len(chunks)}] {chunk['chunk_type']} {chunk['chunk_name']}")

        db.commit()
        print(f"Indexed {len(chunks)} chunks successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    index_codebase("app")