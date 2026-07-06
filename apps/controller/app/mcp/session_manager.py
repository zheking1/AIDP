"""
MCP Session Manager - 强制执行 aidp_context 调用

追踪每个 MCP 会话是否已调用 aidp_context。
未调用则拒绝其他工具调用。
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class MCPSession:
    session_id: str
    context_loaded: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    tools_called: list = field(default_factory=list)
    context_result: Optional[dict] = None

    def touch(self):
        self.last_activity = datetime.now()

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "context_loaded": self.context_loaded,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "tools_called": self.tools_called,
        }


class MCPSessionManager:
    """管理 MCP 会话状态，强制执行 aidp_context 调用顺序。"""

    def __init__(self, timeout_minutes: int = 30):
        self.sessions: Dict[str, MCPSession] = {}
        self.timeout_minutes = timeout_minutes

    def get_or_create_session(self, session_id: str) -> MCPSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = MCPSession(session_id=session_id)
        session = self.sessions[session_id]
        session.touch()
        return session

    def mark_context_loaded(self, session_id: str, context_result: dict = None):
        session = self.get_or_create_session(session_id)
        session.context_loaded = True
        session.context_result = context_result

    def is_context_loaded(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        return session.context_loaded

    def record_tool_call(self, session_id: str, tool_name: str):
        session = self.get_or_create_session(session_id)
        session.tools_called.append({
            "tool": tool_name,
            "time": datetime.now().isoformat(),
        })

    def can_call_tool(self, session_id: str, tool_name: str) -> tuple:
        """检查是否允许调用指定工具。返回 (allowed, reason)。"""
        # 这些工具不需要 aidp_context 前置
        ALLOWED_WITHOUT_CONTEXT = {
            "aidp_context",
            "aidp_init",
            "list_registered_tools",
            "check_tool_health",
            "sync_tool_capabilities",
            "aidp_instructions",
        }

        if tool_name in ALLOWED_WITHOUT_CONTEXT:
            return True, "允许调用"

        session = self.sessions.get(session_id)
        if not session:
            return False, "会话不存在，必须先调用 aidp_context"

        if not session.context_loaded:
            return False, "必须先调用 aidp_context 加载上下文，然后才能调用其他工具"

        return True, "允许调用"

    def cleanup_expired(self):
        now = datetime.now()
        expired = [
            sid for sid, s in self.sessions.items()
            if (now - s.last_activity) > timedelta(minutes=self.timeout_minutes)
        ]
        for sid in expired:
            del self.sessions[sid]
        return len(expired)

    def get_stats(self):
        return {
            "total_sessions": len(self.sessions),
            "sessions_with_context": sum(1 for s in self.sessions.values() if s.context_loaded),
            "sessions_without_context": sum(1 for s in self.sessions.values() if not s.context_loaded),
        }


# 全局单例
session_manager = MCPSessionManager(timeout_minutes=30)
