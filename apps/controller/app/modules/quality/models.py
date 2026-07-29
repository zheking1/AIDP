"""
Quality Module Models
质量检查模型
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, DateTime, Integer
from app.db.database import Base
from app.core.utils import gen_uuid


class CheckResult(Base):
    """检查结果"""
    __tablename__ = "aidp_quality_checks"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(100), nullable=True, index=True)
    filename = Column(String(512), nullable=True)
    language = Column(String(32), nullable=True)
    check_type = Column(String(32), nullable=False, index=True)
    issues = Column(Text, nullable=True)
    issue_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "language": self.language,
            "checkType": self.check_type,
            "issueCount": self.issue_count,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }