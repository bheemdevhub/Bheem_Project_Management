# app/modules/project_management/events/chat_events.py
"""
Chat and Collaboration Events for Project Management Module
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass
from abc import ABC, abstractmethod
import asyncio
import logging

logger = logging.getLogger(__name__)

# ================================
# Base Event Classes
# ================================

@dataclass
class BaseChatEvent:
    """Base class for all chat events"""
    event_id: str
    timestamp: datetime
    user_id: UUID
    
    def __post_init__(self):
        if not self.event_id:
            import uuid
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()

# ================================
# Channel Events
# ================================

@dataclass
class ChannelCreatedEvent(BaseChatEvent):
    """Event fired when a new chat channel is created"""
    channel_id: UUID
    channel_name: str
    created_by: UUID
    member_count: int
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.created_by

@dataclass
class ChannelUpdatedEvent(BaseChatEvent):
    """Event fired when a chat channel is updated"""
    channel_id: UUID
    channel_name: str
    updated_by: UUID
    changes: Dict[str, Any]
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.updated_by

@dataclass
class ChannelDeletedEvent(BaseChatEvent):
    """Event fired when a chat channel is deleted"""
    channel_id: UUID
    channel_name: str
    deleted_by: UUID
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.deleted_by

@dataclass
class ChannelArchivedEvent(BaseChatEvent):
    """Event fired when a chat channel is archived"""
    channel_id: UUID
    channel_name: str
    archived_by: UUID
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.archived_by

# ================================
# Member Events
# ================================

@dataclass
class MemberJoinedEvent(BaseChatEvent):
    """Event fired when a member joins a chat channel"""
    channel_id: UUID
    employee_id: UUID
    added_by: UUID
    role: str = "member"
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.added_by

@dataclass
class MemberLeftEvent(BaseChatEvent):
    """Event fired when a member leaves a chat channel"""
    channel_id: UUID
    employee_id: UUID
    removed_by: UUID
    is_self_removal: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.removed_by

@dataclass
class MemberRoleChangedEvent(BaseChatEvent):
    """Event fired when a member's role is changed"""
    channel_id: UUID
    employee_id: UUID
    old_role: str
    new_role: str
    changed_by: UUID
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.changed_by

# ================================
# Message Events
# ================================

@dataclass
class MessageSentEvent(BaseChatEvent):
    """Event fired when a message is sent"""
    message_id: UUID
    channel_id: UUID
    sender_id: UUID
    content: str
    message_type: str = "text"
    mentioned_users: List[UUID] = None
    parent_message_id: Optional[UUID] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.sender_id
        if self.mentioned_users is None:
            self.mentioned_users = []

@dataclass
class MessageUpdatedEvent(BaseChatEvent):
    """Event fired when a message is updated"""
    message_id: UUID
    channel_id: UUID
    sender_id: UUID
    old_content: str
    new_content: str
    updated_by: UUID
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.updated_by

@dataclass
class MessageDeletedEvent(BaseChatEvent):
    """Event fired when a message is deleted"""
    message_id: UUID
    channel_id: UUID
    sender_id: UUID
    deleted_by: UUID
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.deleted_by

@dataclass
class MessagePinnedEvent(BaseChatEvent):
    """Event fired when a message is pinned"""
    message_id: UUID
    channel_id: UUID
    pinned_by: UUID
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.pinned_by

# ================================
# Reaction Events
# ================================

@dataclass
class ReactionAddedEvent(BaseChatEvent):
    """Event fired when a reaction is added to a message"""
    message_id: UUID
    employee_id: UUID
    emoji: str
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.employee_id

@dataclass
class ReactionRemovedEvent(BaseChatEvent):
    """Event fired when a reaction is removed from a message"""
    message_id: UUID
    employee_id: UUID
    emoji: str
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.employee_id

# ================================
# Direct Message Events
# ================================

@dataclass
class DirectMessageSentEvent(BaseChatEvent):
    """Event fired when a direct message is sent"""
    message_id: UUID
    sender_id: UUID
    recipient_id: UUID
    content: str
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.sender_id

@dataclass
class DirectMessageReadEvent(BaseChatEvent):
    """Event fired when a direct message is read"""
    message_id: UUID
    sender_id: UUID
    recipient_id: UUID
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.recipient_id

# ================================
# Online Status Events
# ================================

@dataclass
class UserOnlineStatusChangedEvent(BaseChatEvent):
    """Event fired when a user's online status changes"""
    employee_id: UUID
    old_status: str
    new_status: str
    custom_status: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.user_id = self.employee_id

# ================================
# Event Handlers
# ================================

class ChatEventHandler(ABC):
    """Abstract base class for chat event handlers"""
    
    @abstractmethod
    async def handle(self, event: BaseChatEvent) -> None:
        """Handle a chat event"""
        pass

class NotificationEventHandler(ChatEventHandler):
    """Handler for sending notifications based on chat events"""
    
    async def handle(self, event: BaseChatEvent) -> None:
        """Send notifications for chat events"""
        try:
            if isinstance(event, MessageSentEvent):
                await self._handle_message_notification(event)
            elif isinstance(event, MemberJoinedEvent):
                await self._handle_member_joined_notification(event)
            elif isinstance(event, DirectMessageSentEvent):
                await self._handle_direct_message_notification(event)
            # Add more event types as needed
                
        except Exception as e:
            logger.error(f"Error handling notification for event {event.event_id}: {str(e)}")
    
    async def _handle_message_notification(self, event: MessageSentEvent) -> None:
        """Handle message notification"""
        # Implementation would integrate with notification service
        logger.info(f"Sending message notification for message {event.message_id}")
        
        # Notify mentioned users
        for user_id in event.mentioned_users:
            logger.info(f"Notifying user {user_id} about mention in message {event.message_id}")
    
    async def _handle_member_joined_notification(self, event: MemberJoinedEvent) -> None:
        """Handle member joined notification"""
        logger.info(f"User {event.employee_id} joined channel {event.channel_id}")
    
    async def _handle_direct_message_notification(self, event: DirectMessageSentEvent) -> None:
        """Handle direct message notification"""
        logger.info(f"Sending DM notification to user {event.recipient_id}")

class ActivityLogEventHandler(ChatEventHandler):
    """Handler for logging chat activities"""
    
    async def handle(self, event: BaseChatEvent) -> None:
        """Log chat activities"""
        try:
            activity_data = {
                "event_type": type(event).__name__,
                "event_id": event.event_id,
                "user_id": str(event.user_id),
                "timestamp": event.timestamp.isoformat(),
                "details": self._extract_event_details(event)
            }
            
            # Log to activity system
            logger.info(f"Chat activity logged: {activity_data}")
            
        except Exception as e:
            logger.error(f"Error logging activity for event {event.event_id}: {str(e)}")
    
    def _extract_event_details(self, event: BaseChatEvent) -> Dict[str, Any]:
        """Extract relevant details from event"""
        details = {}
        
        if hasattr(event, 'channel_id'):
            details['channel_id'] = str(event.channel_id)
        if hasattr(event, 'message_id'):
            details['message_id'] = str(event.message_id)
        if hasattr(event, 'employee_id'):
            details['employee_id'] = str(event.employee_id)
        
        return details

class WebSocketEventHandler(ChatEventHandler):
    """Handler for broadcasting events to WebSocket connections"""
    
    def __init__(self):
        self.connections: Dict[UUID, List] = {}  # user_id -> list of WebSocket connections
    
    async def handle(self, event: BaseChatEvent) -> None:
        """Broadcast event to relevant WebSocket connections"""
        try:
            # Determine which users should receive this event
            target_users = await self._get_target_users(event)
            
            # Broadcast to connected users
            for user_id in target_users:
                if user_id in self.connections:
                    await self._broadcast_to_user(user_id, event)
                    
        except Exception as e:
            logger.error(f"Error broadcasting event {event.event_id}: {str(e)}")
    
    async def _get_target_users(self, event: BaseChatEvent) -> List[UUID]:
        """Determine which users should receive this event"""
        target_users = []
        
        if isinstance(event, (MessageSentEvent, MessageUpdatedEvent, MessageDeletedEvent)):
            # Notify all channel members
            # This would require a database query to get channel members
            target_users = [event.user_id]  # Simplified for now
            
        elif isinstance(event, DirectMessageSentEvent):
            target_users = [event.sender_id, event.recipient_id]
            
        elif isinstance(event, MemberJoinedEvent):
            target_users = [event.employee_id, event.added_by]
        
        return target_users
    
    async def _broadcast_to_user(self, user_id: UUID, event: BaseChatEvent) -> None:
        """Broadcast event to a specific user's connections"""
        if user_id not in self.connections:
            return
        
        event_data = {
            "type": type(event).__name__,
            "data": event.__dict__
        }
        
        # Remove closed connections
        active_connections = []
        for connection in self.connections[user_id]:
            try:
                await connection.send_json(event_data)
                active_connections.append(connection)
            except:
                # Connection is closed
                pass
        
        self.connections[user_id] = active_connections
        if not active_connections:
            del self.connections[user_id]

# ================================
# Event Dispatcher
# ================================

class ChatEventDispatcher:
    """Dispatcher for chat events"""
    
    def __init__(self):
        self.handlers: List[ChatEventHandler] = []
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default event handlers"""
        self.handlers = [
            NotificationEventHandler(),
            ActivityLogEventHandler(),
            WebSocketEventHandler()
        ]
    
    def add_handler(self, handler: ChatEventHandler) -> None:
        """Add an event handler"""
        self.handlers.append(handler)
    
    def remove_handler(self, handler: ChatEventHandler) -> None:
        """Remove an event handler"""
        if handler in self.handlers:
            self.handlers.remove(handler)
    
    async def dispatch(self, event: BaseChatEvent) -> None:
        """Dispatch an event to all handlers"""
        try:
            logger.info(f"Dispatching event: {type(event).__name__} - {event.event_id}")
            
            # Run all handlers concurrently
            tasks = [handler.handle(event) for handler in self.handlers]
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error dispatching event {event.event_id}: {str(e)}")
    
    async def dispatch_multiple(self, events: List[BaseChatEvent]) -> None:
        """Dispatch multiple events"""
        tasks = [self.dispatch(event) for event in events]
        await asyncio.gather(*tasks, return_exceptions=True)

# ================================
# Event Factory
# ================================

class ChatEventFactory:
    """Factory for creating chat events"""
    
    @staticmethod
    def create_channel_created_event(
        channel_id: UUID,
        channel_name: str,
        created_by: UUID,
        member_count: int
    ) -> ChannelCreatedEvent:
        """Create a channel created event"""
        return ChannelCreatedEvent(
            event_id="",
            timestamp=datetime.utcnow(),
            user_id=created_by,
            channel_id=channel_id,
            channel_name=channel_name,
            created_by=created_by,
            member_count=member_count
        )
    
    @staticmethod
    def create_message_sent_event(
        message_id: UUID,
        channel_id: UUID,
        sender_id: UUID,
        content: str,
        mentioned_users: List[UUID] = None,
        parent_message_id: Optional[UUID] = None
    ) -> MessageSentEvent:
        """Create a message sent event"""
        return MessageSentEvent(
            event_id="",
            timestamp=datetime.utcnow(),
            user_id=sender_id,
            message_id=message_id,
            channel_id=channel_id,
            sender_id=sender_id,
            content=content,
            mentioned_users=mentioned_users or [],
            parent_message_id=parent_message_id
        )
    
    @staticmethod
    def create_member_joined_event(
        channel_id: UUID,
        employee_id: UUID,
        added_by: UUID,
        role: str = "member"
    ) -> MemberJoinedEvent:
        """Create a member joined event"""
        return MemberJoinedEvent(
            event_id="",
            timestamp=datetime.utcnow(),
            user_id=added_by,
            channel_id=channel_id,
            employee_id=employee_id,
            added_by=added_by,
            role=role
        )

# Global event dispatcher instance
chat_event_dispatcher = ChatEventDispatcher()
