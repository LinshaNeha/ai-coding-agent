from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id = Column(Integer, primary_key=True, index=True)
    query_hash = Column(String, unique=True, index=True, nullable=False)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    embedding = Column(Vector(3072), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    hit_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())