from typing import Any, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool = True
    code: str = "OK"
    message: str = "success"
    data: Any = None
    trace_id: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    code: str
    message: str
    details: Any = None
    trace_id: Optional[str] = None
