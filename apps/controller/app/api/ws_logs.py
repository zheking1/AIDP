import json
import asyncio
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

connected_clients: list[WebSocket] = []


async def broadcast_invocation(tool_name: str, status: str, duration_ms: int, error: str = None):
    disconnected = []
    payload = json.dumps({
        "tool_name": tool_name,
        "status": status,
        "duration_ms": duration_ms,
        "error": error,
        "timestamp": datetime.utcnow().isoformat(),
    })
    for ws in connected_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in connected_clients:
            connected_clients.remove(ws)


async def ws_handler(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)