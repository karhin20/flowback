"""
WebSocket manager for real-time updates
"""
import json
import asyncio
from typing import Set, Dict, Any
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_metadata[websocket] = {
            "client_id": client_id,
            "connected_at": asyncio.get_event_loop().time()
        }
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        if not self.active_connections:
            return
        
        # Create a copy of connections to avoid modification during iteration
        connections_to_remove = set()
        
        for websocket in self.active_connections.copy():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                connections_to_remove.add(websocket)
        
        # Remove failed connections
        for websocket in connections_to_remove:
            self.disconnect(websocket)
    
    async def broadcast_customer_updated(self, customer_data: Dict[str, Any]):
        message = {
            "type": "customer_updated",
            "payload": customer_data
        }
        await self.broadcast(message)
    
    async def broadcast_customer_created(self, customer_data: Dict[str, Any]):
        message = {
            "type": "customer_created",
            "payload": customer_data
        }
        await self.broadcast(message)
    
    async def broadcast_customer_deleted(self, customer_id: str):
        message = {
            "type": "customer_deleted",
            "payload": {"id": customer_id}
        }
        await self.broadcast(message)
    
    async def broadcast_action_created(self, action_data: Dict[str, Any]):
        message = {
            "type": "action_created",
            "payload": action_data
        }
        await self.broadcast(message)
    
    async def broadcast_dashboard_updated(self, dashboard_data: Dict[str, Any]):
        message = {
            "type": "dashboard_updated",
            "payload": dashboard_data
        }
        await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        return len(self.active_connections)
    
    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "client_id": metadata.get("client_id"),
                    "connected_at": metadata.get("connected_at")
                }
                for metadata in self.connection_metadata.values()
            ]
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()
