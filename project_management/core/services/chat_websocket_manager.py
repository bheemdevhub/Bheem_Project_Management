# app/modules/project_management/core/services/chat_websocket_manager.py
"""
WebSocket Manager for Real-time Chat Features
Handles WebSocket connections, broadcasting, and real-time notifications
"""
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from uuid import UUID
import json
import logging
import asyncio
from datetime import datetime

from bheem_core.modules.project_management.core.schemas.enhanced_chat_schemas import (
    WebSocketMessage, TypingIndicator, OnlineStatusBroadcast
)

logger = logging.getLogger(__name__)

class ChatWebSocketManager:
    """Manages WebSocket connections for chat functionality"""
    
    def __init__(self):
        # Active connections: {channel_id: {user_id: websocket}}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}
        # User to channels mapping: {user_id: set(channel_ids)}
        self.user_channels: Dict[str, Set[str]] = {}
        # Typing indicators: {channel_id: {user_id: timestamp}}
        self.typing_indicators: Dict[str, Dict[str, datetime]] = {}
        
    async def connect(self, websocket: WebSocket, channel_id: UUID, user_id: UUID):
        """Connect a user to a channel"""
        await websocket.accept()
        
        channel_str = str(channel_id)
        user_str = str(user_id)
        
        # Initialize channel if not exists
        if channel_str not in self.connections:
            self.connections[channel_str] = {}
            
        # Add connection
        self.connections[channel_str][user_str] = websocket
        
        # Update user channels mapping
        if user_str not in self.user_channels:
            self.user_channels[user_str] = set()
        self.user_channels[user_str].add(channel_str)
        
        logger.info(f"User {user_id} connected to channel {channel_id}")
        
        # Notify other users in channel
        await self.broadcast_to_channel(
            channel_id=channel_id,
            message={
                "type": "user_joined",
                "user_id": user_str,
                "timestamp": datetime.utcnow().isoformat()
            },
            exclude_user=user_id
        )
        
    async def disconnect(self, channel_id: UUID, user_id: UUID):
        """Disconnect a user from a channel"""
        channel_str = str(channel_id)
        user_str = str(user_id)
        
        # Remove connection
        if channel_str in self.connections and user_str in self.connections[channel_str]:
            del self.connections[channel_str][user_str]
            
        # Update user channels mapping
        if user_str in self.user_channels:
            self.user_channels[user_str].discard(channel_str)
            if not self.user_channels[user_str]:
                del self.user_channels[user_str]
                
        # Remove typing indicator
        if channel_str in self.typing_indicators and user_str in self.typing_indicators[channel_str]:
            del self.typing_indicators[channel_str][user_str]
            
        # Clean up empty channel
        if channel_str in self.connections and not self.connections[channel_str]:
            del self.connections[channel_str]
            
        logger.info(f"User {user_id} disconnected from channel {channel_id}")
        
        # Notify other users in channel
        await self.broadcast_to_channel(
            channel_id=channel_id,
            message={
                "type": "user_left",
                "user_id": user_str,
                "timestamp": datetime.utcnow().isoformat()
            },
            exclude_user=user_id
        )
        
    async def broadcast_to_channel(
        self, 
        channel_id: UUID, 
        message: Dict[str, Any], 
        exclude_user: Optional[UUID] = None
    ):
        """Broadcast a message to all users in a channel"""
        channel_str = str(channel_id)
        exclude_str = str(exclude_user) if exclude_user else None
        
        if channel_str not in self.connections:
            return
            
        # Get all connections in channel
        connections = self.connections[channel_str].copy()
        
        # Remove connections that should be excluded
        if exclude_str and exclude_str in connections:
            del connections[exclude_str]
            
        # Send to all remaining connections
        if connections:
            await self._send_to_connections(connections.values(), message)
            
    async def broadcast_to_user(self, user_id: UUID, message: Dict[str, Any]):
        """Broadcast a message to a user across all their channels"""
        user_str = str(user_id)
        
        if user_str not in self.user_channels:
            return
            
        # Collect all websockets for this user
        user_websockets = []
        for channel_id in self.user_channels[user_str]:
            if (channel_id in self.connections and 
                user_str in self.connections[channel_id]):
                user_websockets.append(self.connections[channel_id][user_str])
                
        # Send to all user's websockets
        if user_websockets:
            await self._send_to_connections(user_websockets, message)
            
    async def handle_new_message(
        self, 
        channel_id: UUID, 
        message_data: Dict[str, Any], 
        sender_id: UUID
    ):
        """Handle broadcasting of new messages"""
        message = {
            "type": "new_message",
            "channel_id": str(channel_id),
            "message": message_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_channel(channel_id, message, exclude_user=sender_id)
        
    async def handle_message_update(
        self, 
        channel_id: UUID, 
        message_data: Dict[str, Any], 
        updated_by: UUID
    ):
        """Handle broadcasting of message updates"""
        message = {
            "type": "message_updated",
            "channel_id": str(channel_id),
            "message": message_data,
            "updated_by": str(updated_by),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_channel(channel_id, message)
        
    async def handle_message_deletion(
        self, 
        channel_id: UUID, 
        message_id: UUID, 
        deleted_by: UUID
    ):
        """Handle broadcasting of message deletions"""
        message = {
            "type": "message_deleted",
            "channel_id": str(channel_id),
            "message_id": str(message_id),
            "deleted_by": str(deleted_by),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_channel(channel_id, message)
        
    async def handle_reaction_added(
        self, 
        channel_id: UUID, 
        message_id: UUID, 
        reaction_data: Dict[str, Any], 
        user_id: UUID
    ):
        """Handle broadcasting of reaction additions"""
        message = {
            "type": "reaction_added",
            "channel_id": str(channel_id),
            "message_id": str(message_id),
            "reaction": reaction_data,
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_channel(channel_id, message, exclude_user=user_id)
        
    async def handle_reaction_removed(
        self, 
        channel_id: UUID, 
        message_id: UUID, 
        emoji: str, 
        user_id: UUID
    ):
        """Handle broadcasting of reaction removals"""
        message = {
            "type": "reaction_removed",
            "channel_id": str(channel_id),
            "message_id": str(message_id),
            "emoji": emoji,
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_channel(channel_id, message, exclude_user=user_id)
        
    async def handle_typing_indicator(
        self, 
        channel_id: UUID, 
        user_id: UUID, 
        is_typing: bool
    ):
        """Handle typing indicators"""
        channel_str = str(channel_id)
        user_str = str(user_id)
        
        # Update typing indicator state
        if channel_str not in self.typing_indicators:
            self.typing_indicators[channel_str] = {}
            
        if is_typing:
            self.typing_indicators[channel_str][user_str] = datetime.utcnow()
        else:
            self.typing_indicators[channel_str].pop(user_str, None)
            
        # Broadcast typing indicator
        message = {
            "type": "typing_indicator",
            "channel_id": channel_str,
            "user_id": user_str,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_channel(channel_id, message, exclude_user=user_id)
        
    async def handle_member_added(
        self, 
        channel_id: UUID, 
        member_data: Dict[str, Any], 
        added_by: UUID
    ):
        """Handle broadcasting when member is added to channel"""
        message = {
            "type": "member_added",
            "channel_id": str(channel_id),
            "member": member_data,
            "added_by": str(added_by),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_channel(channel_id, message)
        
    async def handle_member_removed(
        self, 
        channel_id: UUID, 
        employee_id: UUID, 
        removed_by: UUID
    ):
        """Handle broadcasting when member is removed from channel"""
        message = {
            "type": "member_removed",
            "channel_id": str(channel_id),
            "employee_id": str(employee_id),
            "removed_by": str(removed_by),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_channel(channel_id, message)
        
    async def handle_online_status_change(
        self, 
        user_id: UUID, 
        status_data: Dict[str, Any]
    ):
        """Handle broadcasting of online status changes"""
        message = {
            "type": "status_change",
            "user_id": str(user_id),
            "status": status_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to all channels where user is a member
        await self.broadcast_to_user(user_id, message)
        
    async def handle_direct_message(
        self, 
        recipient_id: UUID, 
        message_data: Dict[str, Any], 
        sender_id: UUID
    ):
        """Handle broadcasting of direct messages"""
        message = {
            "type": "direct_message",
            "message": message_data,
            "sender_id": str(sender_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_user(recipient_id, message)
        
    async def get_channel_users(self, channel_id: UUID) -> List[str]:
        """Get list of users currently connected to a channel"""
        channel_str = str(channel_id)
        
        if channel_str not in self.connections:
            return []
            
        return list(self.connections[channel_str].keys())
        
    async def get_typing_users(self, channel_id: UUID) -> List[str]:
        """Get list of users currently typing in a channel"""
        channel_str = str(channel_id)
        
        if channel_str not in self.typing_indicators:
            return []
            
        # Filter out expired typing indicators (older than 10 seconds)
        current_time = datetime.utcnow()
        active_typing = []
        
        for user_id, timestamp in self.typing_indicators[channel_str].items():
            if (current_time - timestamp).total_seconds() < 10:
                active_typing.append(user_id)
            else:
                # Remove expired typing indicator
                del self.typing_indicators[channel_str][user_id]
                
        return active_typing
        
    async def _send_to_connections(self, connections: List[WebSocket], message: Dict[str, Any]):
        """Send message to multiple WebSocket connections"""
        if not connections:
            return
            
        # Convert message to JSON
        message_json = json.dumps(message)
        
        # Send to all connections concurrently
        tasks = []
        for websocket in connections:
            tasks.append(self._safe_send(websocket, message_json))
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def _safe_send(self, websocket: WebSocket, message: str):
        """Safely send message to WebSocket connection"""
        try:
            await websocket.send_text(message)
        except WebSocketDisconnect:
            # Connection already closed
            pass
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {str(e)}")
            
    async def cleanup_expired_typing_indicators(self):
        """Clean up expired typing indicators (run periodically)"""
        current_time = datetime.utcnow()
        
        for channel_id in list(self.typing_indicators.keys()):
            for user_id in list(self.typing_indicators[channel_id].keys()):
                timestamp = self.typing_indicators[channel_id][user_id]
                if (current_time - timestamp).total_seconds() > 10:
                    del self.typing_indicators[channel_id][user_id]
                    
            # Clean up empty channels
            if not self.typing_indicators[channel_id]:
                del self.typing_indicators[channel_id]

# Global WebSocket manager instance
chat_websocket_manager = ChatWebSocketManager()

# Background task to clean up expired typing indicators
async def typing_cleanup_task():
    """Background task to clean up expired typing indicators"""
    while True:
        await asyncio.sleep(30)  # Run every 30 seconds
        await chat_websocket_manager.cleanup_expired_typing_indicators()

# Start the cleanup task when the module is imported
# asyncio.create_task(typing_cleanup_task())

