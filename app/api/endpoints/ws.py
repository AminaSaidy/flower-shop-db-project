from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List

router = APIRouter(tags=["websocket"])

_connections: Dict[str, List[WebSocket]] = {}


@router.websocket("/ws/orders/{order_id}")
async def order_status_ws(websocket: WebSocket, order_id: str):
    await websocket.accept()

    if order_id not in _connections:
        _connections[order_id] = []
    _connections[order_id].append(websocket)

    try:
        await websocket.send_json({"type": "connected", "order_id": order_id})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections[order_id].remove(websocket)


async def notify_order_update(order_id: str, new_status: str):
    if order_id not in _connections:
        return
    dead = []
    for ws in _connections[order_id]:
        try:
            await ws.send_json({"type": "status_update",
                                "order_id": order_id,
                                "status": new_status})
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections[order_id].remove(ws)