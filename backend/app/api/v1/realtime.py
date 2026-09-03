import asyncio
import json

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.config import Settings, get_settings
from app.core.deps import get_current_user
from app.db.session import SessionLocal
from app.models.user import User
from app.security.auth import decode_token
from app.services.realtime import broker, snapshot

router = APIRouter(tags=["realtime"])
ws_router = APIRouter(tags=["realtime"])


@router.get("/realtime/snapshot")
async def realtime_snapshot(
    line_id: str = Query(default="line-1", min_length=1, max_length=64),
    _: User = Depends(get_current_user),
) -> dict:
    return await snapshot(line_id)


@ws_router.websocket("/ws/realtime")
async def realtime_websocket(
    websocket: WebSocket,
    line_id: str = Query(default="line-1", min_length=1, max_length=64),
    access_token: str = Query(default=""),
    settings: Settings = Depends(get_settings),
) -> None:
    try:
        payload = decode_token(settings, access_token, "access")
        async with SessionLocal() as session:
            user = await session.get(User, int(payload["sub"]))
        if user is None or user.status != "active":
            raise ValueError("user unavailable")
    except (ValueError, TypeError, KeyError):
        await websocket.close(code=4401, reason="unauthorized")
        return

    await websocket.accept()
    queue = broker.subscribe(line_id)
    try:
        hello = broker.envelope("HELLO", {"line_id": line_id, "snapshot": await snapshot(line_id)}, line_id)
        await websocket.send_text(json.dumps(hello, ensure_ascii=False))
        async def forward_events() -> None:
            while True:
                await websocket.send_text(await queue.get())

        sender = asyncio.create_task(forward_events())
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=45)
            except TimeoutError:
                await websocket.close(code=4408, reason="heartbeat timeout")
                return
            except WebSocketDisconnect:
                return
            try:
                incoming = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps(broker.envelope("ERROR", {"message": "invalid JSON"}, line_id)))
                continue
            if incoming.get("type") == "PING":
                await websocket.send_text(json.dumps(broker.envelope("PONG", {}, line_id)))
                continue
            if incoming.get("type") not in {"PING", "PONG"}:
                await websocket.send_text(json.dumps(broker.envelope("ERROR", {"message": "unsupported message"}, line_id)))
    finally:
        if "sender" in locals():
            sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)
        broker.unsubscribe(line_id, queue)
