"""
WebSocket connection manager — real-time event broadcasting.

Manages authenticated WebSocket connections with workspace-level
isolation. Users only receive events for workspaces they belong to.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect, status

from app.core.logging import get_logger
from app.core.security import decode_token

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with workspace isolation.

    Each connection is tied to a (user_id, workspace_id) pair.
    Broadcasts are filtered so users only receive events for
    workspaces they are connected to.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[dict[str, Any]]] = {}  # workspace_id -> connections

    async def connect(
        self,
        websocket: WebSocket,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Accept a new WebSocket connection and track it."""
        await websocket.accept()
        ws_id = str(workspace_id)
        if ws_id not in self._connections:
            self._connections[ws_id] = []
        self._connections[ws_id].append({
            "websocket": websocket,
            "user_id": str(user_id),
            "workspace_id": ws_id,
        })
        logger.debug(
            "WebSocket connected",
            user_id=str(user_id),
            workspace_id=ws_id,
            total_connections=sum(len(v) for v in self._connections.values()),
        )

    def disconnect(self, websocket: WebSocket, workspace_id: uuid.UUID) -> None:
        """Remove a WebSocket connection."""
        ws_id = str(workspace_id)
        if ws_id in self._connections:
            self._connections[ws_id] = [
                c for c in self._connections[ws_id] if c["websocket"] != websocket
            ]
            if not self._connections[ws_id]:
                del self._connections[ws_id]

    async def broadcast_to_workspace(
        self,
        workspace_id: uuid.UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Broadcast an event to all connections in a workspace.

        Returns the number of connections that received the message.
        Failed connections are cleaned up automatically.
        """
        ws_id = str(workspace_id)
        if ws_id not in self._connections:
            return 0

        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        })

        stale = []
        count = 0
        for conn in self._connections[ws_id]:
            try:
                await conn["websocket"].send_text(message)
                count += 1
            except WebSocketDisconnect:
                stale.append(conn)
            except Exception as exc:
                logger.warning("WebSocket send failed", error=str(exc))
                stale.append(conn)

        # Clean up stale connections
        for conn in stale:
            self._connections[ws_id].remove(conn)

        return count

    async def broadcast_to_user(
        self,
        user_id: uuid.UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """Broadcast an event to all connections for a specific user."""
        uid = str(user_id)
        message = json.dumps({
            "type": event_type,
            "data": data,
        })
        count = 0
        for ws_list in self._connections.values():
            for conn in ws_list:
                if conn["user_id"] == uid:
                    try:
                        await conn["websocket"].send_text(message)
                        count += 1
                    except Exception:
                        pass
        return count

    def get_workspace_connections(self, workspace_id: uuid.UUID) -> int:
        """Get the number of active connections in a workspace."""
        ws_id = str(workspace_id)
        return len(self._connections.get(ws_id, []))

    def get_total_connections(self) -> int:
        """Get total active connections across all workspaces."""
        return sum(len(v) for v in self._connections.values())


# Global WebSocket connection manager
ws_manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket) -> tuple[uuid.UUID, uuid.UUID] | None:
    """Authenticate a WebSocket connection via query parameter token."""
    token = websocket.query_params.get("token")
    workspace_id_str = websocket.query_params.get("workspace_id")

    if not token or not workspace_id_str:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token or workspace_id")
        return None

    try:
        payload = decode_token(token)
        user_id = uuid.UUID(payload.get("sub", ""))
        workspace_id = uuid.UUID(workspace_id_str)
        return user_id, workspace_id
    except Exception as exc:
        logger.warning("WebSocket auth failed", error=str(exc))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return None
