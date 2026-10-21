"""
WebSocket Connection Manager for live dashboard log streaming.
"""

import json
import asyncio
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from config.logger import logger


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        payload = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                disconnected.append(connection)

        for dead in disconnected:
            self.disconnect(dead)

    def broadcast_sync(self, message: Dict[str, Any]):
        """Helper to broadcast from synchronous background tasks or threads."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
            else:
                loop.run_until_complete(self.broadcast(message))
        except Exception:
            pass


manager = ConnectionManager()
