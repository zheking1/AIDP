"""
Shared utility functions for AIDP modules
"""

import uuid
from datetime import datetime, timezone


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_current_user_id(user) -> str:
    uid = getattr(user, 'id', None) or getattr(user, 'username', None)
    return str(uid) if uid else None
