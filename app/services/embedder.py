from google import genai
from app.core.config import GEMINI_API_KEY

EMBEDDING_MODEL = "gemini-embedding-001"  # outputs 768-dim vectors


class Embedder:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def embed_text(self, text: str) -> list[float]:
        """Returns a single embedding vector for one piece of text."""
        result = self.client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text
        )
        return result.embeddings[0].values

    def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        """Takes indexer output, adds an 'embedding' key to each chunk dict."""
        for chunk in chunks:
            chunk["embedding"] = self.embed_text(chunk["content"])
        return chunks