from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(64), nullable=False)
    content = Column(Text)
    status = Column(String(32), default="pending")
    review_comment = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
