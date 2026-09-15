from app.core.database import Base, engine
from app.models.request_log import RequestLog
from app.models.cache_entry import CacheEntry
from app.models.code_chunk import CodeChunk

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()