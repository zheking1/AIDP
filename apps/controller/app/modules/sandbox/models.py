"""
Sandbox Module Models
代码沙箱模型
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from app.db.database import Base
from app.core.utils import gen_uuid


class Execution(Base):
    """代码执行记录"""
    __tablename__ = "aidp_sandbox_executions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(100), nullable=True, index=True)
    language = Column(String(32), nullable=False, index=True)
    code = Column(Text, nullable=False)
    stdin = Column(Text, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    timed_out = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Integer, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "language": self.language,
            "code": self.code[:200],
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exitCode": self.exit_code,
            "timedOut": self.timed_out,
            "durationMs": self.duration_ms,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }