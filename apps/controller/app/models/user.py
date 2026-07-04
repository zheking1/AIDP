from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), default="user")
    created_at = Column(DateTime, server_default=func.now())
