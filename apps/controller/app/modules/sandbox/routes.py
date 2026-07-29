"""
Sandbox Module Routes
代码沙箱 API 路由
"""
import asyncio, time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import async_session_factory
from app.modules.sandbox.models import Execution
from app.core.permissions import require_permissions
from app.api.auth import get_current_user

router = APIRouter()

SUPPORTED_LANGUAGES = {
    "python": {"ext": ".py", "cmd": ["python3", "-u"]},
    "bash": {"ext": ".sh", "cmd": ["bash"]},
    "sh": {"ext": ".sh", "cmd": ["sh"]},
}

EXECUTION_TIMEOUT = 30
EXECUTION_MAX_OUTPUT = 10240


class ExecuteRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field("python")
    stdin: Optional[str] = None


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


@router.post("/execute")
async def run_code(
    data: ExecuteRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    lang = data.language
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")

    lang_info = SUPPORTED_LANGUAGES[lang]
    tmp_file = f"/tmp/sandbox_exec_{id(data)}{lang_info['ext']}"
    with open(tmp_file, "w") as f:
        f.write(data.code)

    start = time.time()
    timed_out = False
    stdout = stderr = ""
    exit_code = -1

    try:
        proc = await asyncio.create_subprocess_exec(
            *lang_info["cmd"], tmp_file,
            stdin=asyncio.subprocess.PIPE if data.stdin else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out_b, err_b = await asyncio.wait_for(
                proc.communicate(input=data.stdin.encode() if data.stdin else None),
                timeout=EXECUTION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            timed_out = True
            out_b, err_b = b"", b"Execution timed out"
        stdout = out_b.decode(errors="replace")[:EXECUTION_MAX_OUTPUT]
        stderr = err_b.decode(errors="replace")[:EXECUTION_MAX_OUTPUT]
        exit_code = proc.returncode
    except Exception as e:
        stderr = str(e)

    duration_ms = int((time.time() - start) * 1000)
    exec_record = Execution(
        user_id=str(getattr(user, 'id', '') or ''),
        language=lang, code=data.code, stdin=data.stdin,
        stdout=stdout, stderr=stderr, exit_code=exit_code,
        timed_out=timed_out, duration_ms=duration_ms,
    )
    db.add(exec_record)
    await db.commit()
    await db.refresh(exec_record)

    return {
        "id": exec_record.id, "language": lang,
        "stdout": stdout, "stderr": stderr,
        "exitCode": exit_code, "timedOut": timed_out,
        "durationMs": duration_ms,
    }


@router.get("/history")
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Execution).order_by(desc(Execution.created_at)).limit(limit)
    )
    return [r.to_dict() for r in result.scalars().all()]