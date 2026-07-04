from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class AgentInstruction(Base):
    __tablename__ = "agent_instructions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False, default=0)
    agent_type = Column(String(100), nullable=False, default="main")
    role = Column(Text)
    constraints = Column(JSON, default=dict)
    rules = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())