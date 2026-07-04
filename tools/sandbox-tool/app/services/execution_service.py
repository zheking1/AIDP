import asyncio
import time
import logging
from typing import Optional

from sqlalchemy import select
from app.db.models import Execution, async_session
from app.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "python": {"ext": ".py", "cmd": ["python3", "-u"]},
    "bash": {"ext": ".sh", "cmd": ["bash"]},
    "sh": {"ext": ".sh", "cmd": ["sh"]},
}


async def execute_code(
    code: str,
    language: str,
    stdin: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    if language not in SUPPORTED_LANGUAGES:
        return {"error": f"Unsupported language: {language}. Supported: {list(SUPPORTED_LANGUAGES.keys())}"}

    lang_info = SUPPORTED_LANGUAGES[language]
    ext = lang_info["ext"]
    cmd = lang_info["cmd"]

    tmp_file = f"/tmp/sandbox_exec{ext}"

    with open(tmp_file, "w") as f:
        f.write(code)

    start = time.time()
    timed_out = False

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, tmp_file,
            stdin=asyncio.subprocess.PIPE if stdin else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin.encode() if stdin else None),
                timeout=settings.EXECUTION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            timed_out = True
            stdout_bytes, stderr_bytes = b"", b"Execution timed out"

        stdout = stdout_bytes.decode(errors="replace")[:settings.EXECUTION_MAX_OUTPUT]
        stderr = stderr_bytes.decode(errors="replace")[:settings.EXECUTION_MAX_OUTPUT]
        exit_code = proc.returncode
        duration_ms = int((time.time() - start) * 1000)

    except Exception as e:
        stdout, stderr, exit_code, duration_ms = "", str(e), -1, 0

    async with async_session() as session:
        record = Execution(
            user_id=user_id,
            language=language,
            code=code,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
            duration_ms=duration_ms,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

    return {
        "id": record.id,
        "language": language,
        "stdout": stdout,
        "stderr": stderr,
        "exitCode": exit_code,
        "timedOut": timed_out,
        "durationMs": duration_ms,
    }


async def get_history(user_id: Optional[int] = None, limit: int = 20) -> list:
    async with async_session() as session:
        q = select(Execution)
        if user_id:
            q = q.where(Execution.user_id == user_id)
        q = q.order_by(Execution.id.desc()).limit(limit)
        result = await session.execute(q)
        return [
            {
                "id": r.id,
                "language": r.language,
                "code": r.code[:200],
                "exitCode": r.exit_code,
                "timedOut": r.timed_out,
                "durationMs": r.duration_ms,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]
