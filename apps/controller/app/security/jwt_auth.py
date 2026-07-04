import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

SECRET_KEY = os.getenv("JWT_SECRET", "aidp-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[Dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
