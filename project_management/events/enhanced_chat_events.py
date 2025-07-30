# app/modules/project_management/events/enhanced_chat_events.py
"""
Enhanced Chat and Collaboration Events for Project Management Module
Comprehensive event system for chat functionality
"""
from typing import Optional, List, Dict, Any
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
class BaseChatEvent(ABC):
    """Base class for all chat-related events"""
    timestamp: datetime
    
    @abstractmethod
    def get_event_type(self) -> str:
        """Get the event type identifier"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'event_type': self.get_event_type(),
            'timestamp': self.timestamp.isoformat(),
            **self.__dict__
        }

# ================================
# Channel Events
# ================================

@dataclass
class ChannelCreatedEvent(BaseChatEvent):
    """Event fired when a new channel is created"""
    channel_id: UUID
    channel_name: str
    channel_type: str
    created_by: UUID
    project_id: Optional[UUID] = None
    
    def get_event_type(self) -> str:
        return "chat.channel.created"

@dataclass
class ChannelUpdatedEvent(BaseChatEvent):
    """Event fired when a channel is updated"""
    channel_id: UUID
    channel_name: str
    updated_by: UUID
    changes: Dict[str, Any]
    
    def get_event_type(self) -> str:
        return "chat.channel.updated"

@dataclass
class ChannelDeletedEvent(BaseChatEvent):
    """Event fired when a channel is deleted"""
    channel_id: UUID
    channel_name: str
    deleted_by: UUID
    hard_delete: bool = False
    
    def get_event_type(self) -> str:
        return "chat.channel.deleted"

@dataclass
class ChannelArchivedEvent(BaseChatEvent):
    """Event fired when a channel is archived"""
    channel_id: UUID
    channel_name: str
    archived_by: UUID
    
    def get_event_type(self) -> str:
        return "chat.channel.archived"

# ================================
# Member Events
# ================================

@dataclass
class MemberJoinedEvent(BaseChatEvent):
    """Event fired when a member joins a channel"""
    channel_id: UUID
    employee_id: UUID
    role: str
    added_by: UUID
    
    def get_event_type(self) -> str:
        return "chat.member.joined"

@dataclass
class MemberLeftEvent(BaseChatEvent):
    """Event fired when a member leaves a channel"""
    channel_id: UUID
    employee_id: UUID
    removed_by: UUID
    
    def get_event_type(self) -> str:
        return "chat.member.left"

@dataclass
class MemberRoleChangedEvent(BaseChatEvent):
    """Event fired when a member's role is changed"""
    channel_id: UUID
    employee_id: UUID
    old_role: str
    new_role: str
    updated_by: UUID
    
    def get_event_type(self) -> str:
        return "chat.member.role_changed"

@dataclass
class BulkMembersAddedEvent(BaseChatEvent):
    """Event fired when multiple members are added to a channel"""
    channel_id: UUID
    employee_ids: List[UUID]
    role: str
    added_by: UUID
    success_count: int
    failure_count: int
    
    def get_event_type(self) -> str:
        return "chat.members.bulk_added"

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
    message_type: str
    mentioned_users: List[UUID]
    parent_message_id: Optional[UUID] = None
    
    def get_event_type(self) -> str:
        return "chat.message.sent"

@dataclass
class MessageUpdatedEvent(BaseChatEvent):
    """Event fired when a message is updated"""
    message_id: UUID
    channel_id: UUID
    updated_by: UUID
    changes: Dict[str, Any]
    
    def get_event_type(self) -> str:
        return "chat.message.updated"

@dataclass
class MessageDeletedEvent(BaseChatEvent):
    """Event fired when a message is deleted"""
    message_id: UUID
    channel_id: UUID
    deleted_by: UUID
    hard_delete: bool = False
    
    def get_event_type(self) -> str:
        return "chat.message.deleted"

@dataclass
class MessagePinnedEvent(BaseChatEvent):
    """Event fired when a message is pinned"""
    message_id: UUID
    channel_id: UUID
    pinned_by: UUID
    
    def get_event_type(self) -> str:
        return "chat.message.pinned"

@dataclass
class MessageUnpinnedEvent(BaseChatEvent):
    """Event fired when a message is unpinned"""
    message_id: UUID
    channel_id: UUID
    unpinned_by: UUID
    
    def get_event_type(self) -> str:
        return "chat.message.unpinned"

@dataclass
class ThreadStartedEvent(BaseChatEvent):
    """Event fired when a thread is started"""
    parent_message_id: UUID
    first_reply_id: UUID
    channel_id: UUID
    started_by: UUID
    
    def get_event_type(self) -> str:
        return "chat.thread.started"

# ================================
# Reaction Events
# ================================

@dataclass
class ReactionAddedEvent(BaseChatEvent):
    """Event fired when a reaction is added to a message"""
    reaction_id: UUID
    message_id: UUID
    employee_id: UUID
    emoji: str
    
    def get_event_type(self) -> str:
        return "chat.reaction.added"

@dataclass
class ReactionRemovedEvent(BaseChatEvent):
    """Event fired when a reaction is removed from a message"""
    reaction_id: UUID
    message_id: UUID
    employee_id: UUID
    emoji: str
    
    def get_event_type(self) -> str:
        return "chat.reaction.removed"

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
    
    def get_event_type(self) -> str:
        return "chat.direct_message.sent"

@dataclass
class DirectMessageReadEvent(BaseChatEvent):
    """Event fired when direct messages are marked as read"""
    sender_id: UUID
    recipient_id: UUID
    messages_read_count: int
    
    def get_event_type(self) -> str:
        return "chat.direct_message.read"

# ================================
# Online Status Events
# ================================

@dataclass
class OnlineStatusChangedEvent(BaseChatEvent):
    """Event fired when user's online status changes"""
    employee_id: UUID
    old_status: str
    new_status: str
    custom_status: Optional[str] = None
    
    def get_event_type(self) -> str:
        return "chat.status.changed"

@dataclass
class UserWentOfflineEvent(BaseChatEvent):
    """Event fired when user goes offline (auto-detected)"""
    employee_id: UUID
    last_seen: datetime
    
    def get_event_type(self) -> str:
        return "chat.status.offline"

# ================================
# Real-time Communication Events
# ================================

@dataclass
class TypingStartedEvent(BaseChatEvent):
    """Event fired when user starts typing"""
    channel_id: UUID
    employee_id: UUID
    
    def get_event_type(self) -> str:
        return "chat.typing.started"

@dataclass
class TypingStoppedEvent(BaseChatEvent):
    """Event fired when user stops typing"""
    channel_id: UUID
    employee_id: UUID
    
    def get_event_type(self) -> str:
        return "chat.typing.stopped"

@dataclass
class UserJoinedChannelOnlineEvent(BaseChatEvent):
    """Event fired when user comes online in a channel"""
    channel_id: UUID
    employee_id: UUID
    
    def get_event_type(self) -> str:
        return "chat.channel.user_online"

@dataclass
class UserLeftChannelOnlineEvent(BaseChatEvent):
    """Event fired when user goes offline in a channel"""
    channel_id: UUID
    employee_id: UUID
    
    def get_event_type(self) -> str:
        return "chat.channel.user_offline"

# ================================
# Analytics Events
# ================================

@dataclass
class ChannelActivitySpikEvent(BaseChatEvent):
    """Event fired when channel activity spikes"""
    channel_id: UUID
    message_count_last_hour: int
    threshold_exceeded: int
    
    def get_event_type(self) -> str:
        return "chat.analytics.activity_spike"

@dataclass
class DailyUsageReportEvent(BaseChatEvent):
    """Event fired for daily usage reporting"""
    total_messages: int
    total_active_users: int
    total_channels_active: int
    peak_concurrent_users: int
    
    def get_event_type(self) -> str:
        return "chat.analytics.daily_report"

# ================================
# Moderation Events
# ================================

@dataclass
class MessageFlaggedEvent(BaseChatEvent):
    """Event fired when a message is flagged for moderation"""
    message_id: UUID
    channel_id: UUID
    flagged_by: UUID
    reason: str
    
    def get_event_type(self) -> str:
        return "chat.moderation.message_flagged"

@dataclass
class UserMutedEvent(BaseChatEvent):
    """Event fired when a user is muted in a channel"""
    channel_id: UUID
    employee_id: UUID
    muted_by: UUID
    duration_minutes: Optional[int] = None
    
    def get_event_type(self) -> str:
        return "chat.moderation.user_muted"

@dataclass
class UserUnmutedEvent(BaseChatEvent):
    """Event fired when a user is unmuted in a channel"""
    channel_id: UUID
    employee_id: UUID
    unmuted_by: UUID
    
    def get_event_type(self) -> str:
        return "chat.moderation.user_unmuted"

# ================================
# Integration Events
# ================================

@dataclass
class ExternalMessageEvent(BaseChatEvent):
    """Event fired when message comes from external integration"""
    message_id: UUID
    channel_id: UUID
    external_source: str
    external_user_id: str
    content: str
    
    def get_event_type(self) -> str:
        return "chat.integration.external_message"

@dataclass
class WebhookTriggeredEvent(BaseChatEvent):
    """Event fired when a webhook is triggered"""
    webhook_id: UUID
    channel_id: UUID
    trigger_event: str
    payload: Dict[str, Any]
    
    def get_event_type(self) -> str:
        return "chat.integration.webhook_triggered"

# ================================
# Event Listeners
# ================================

class ChatEventListener(ABC):
    """Abstract base class for chat event listeners"""
    
    @abstractmethod
    async def handle_event(self, event: BaseChatEvent) -> None:
        """Handle a chat event"""
        pass

class NotificationEventListener(ChatEventListener):
    """Event listener for sending notifications"""
    
    async def handle_event(self, event: BaseChatEvent) -> None:
        """Handle event for notifications"""
        try:
            # Send notifications based on event type
            if isinstance(event, MessageSentEvent):
                await self._send_message_notification(event)
            elif isinstance(event, MemberJoinedEvent):
                await self._send_member_joined_notification(event)
            elif isinstance(event, DirectMessageSentEvent):
                await self._send_direct_message_notification(event)
            elif isinstance(event, ReactionAddedEvent):
                await self._send_reaction_notification(event)
            
            logger.debug(f"Notification sent for event: {event.get_event_type()}")
            
        except Exception as e:
            logger.error(f"Failed to send notification for event {event.get_event_type()}: {str(e)}")
    
    async def _send_message_notification(self, event: MessageSentEvent) -> None:
        """Send notification for new message"""
        # Implementation would integrate with notification service
        pass
    
    async def _send_member_joined_notification(self, event: MemberJoinedEvent) -> None:
        """Send notification for member joined"""
        # Implementation would integrate with notification service
        pass
    
    async def _send_direct_message_notification(self, event: DirectMessageSentEvent) -> None:
        """Send notification for direct message"""
        # Implementation would integrate with notification service
        pass
    
    async def _send_reaction_notification(self, event: ReactionAddedEvent) -> None:
        """Send notification for reaction"""
        # Implementation would integrate with notification service
        pass

class AnalyticsEventListener(ChatEventListener):
    """Event listener for chat analytics"""
    
    async def handle_event(self, event: BaseChatEvent) -> None:
        """Handle event for analytics"""
        try:
            # Track analytics based on event type
            if isinstance(event, MessageSentEvent):
                await self._track_message_sent(event)
            elif isinstance(event, ChannelCreatedEvent):
                await self._track_channel_created(event)
            elif isinstance(event, MemberJoinedEvent):
                await self._track_member_activity(event)
            
            logger.debug(f"Analytics tracked for event: {event.get_event_type()}")
            
        except Exception as e:
            logger.error(f"Failed to track analytics for event {event.get_event_type()}: {str(e)}")
    
    async def _track_message_sent(self, event: MessageSentEvent) -> None:
        """Track message sending metrics"""
        # Implementation would integrate with analytics service
        pass
    
    async def _track_channel_created(self, event: ChannelCreatedEvent) -> None:
        """Track channel creation metrics"""
        # Implementation would integrate with analytics service
        pass
    
    async def _track_member_activity(self, event: MemberJoinedEvent) -> None:
        """Track member activity metrics"""
        # Implementation would integrate with analytics service
        pass

class AuditLogEventListener(ChatEventListener):
    """Event listener for audit logging"""
    
    async def handle_event(self, event: BaseChatEvent) -> None:
        """Handle event for audit logging"""
        try:
            # Log all events for audit trail
            audit_entry = {
                'event_type': event.get_event_type(),
                'timestamp': event.timestamp.isoformat(),
                'event_data': event.to_dict()
            }
            
            # Save to audit log
            await self._save_audit_log(audit_entry)
            
            logger.debug(f"Audit log created for event: {event.get_event_type()}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log for event {event.get_event_type()}: {str(e)}")
    
    async def _save_audit_log(self, audit_entry: Dict[str, Any]) -> None:
        """Save audit log entry"""
        # Implementation would integrate with audit logging service
        pass

class WebSocketEventListener(ChatEventListener):
    """Event listener for real-time WebSocket updates"""
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
    
    async def handle_event(self, event: BaseChatEvent) -> None:
        """Handle event for WebSocket broadcasting"""
        try:
            if not self.websocket_manager:
                return
            
            # Broadcast real-time events to connected clients
            if isinstance(event, MessageSentEvent):
                await self._broadcast_message(event)
            elif isinstance(event, OnlineStatusChangedEvent):
                await self._broadcast_status_change(event)
            elif isinstance(event, TypingStartedEvent):
                await self._broadcast_typing_indicator(event)
            elif isinstance(event, ReactionAddedEvent):
                await self._broadcast_reaction(event)
            
            logger.debug(f"WebSocket broadcast sent for event: {event.get_event_type()}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast WebSocket event {event.get_event_type()}: {str(e)}")
    
    async def _broadcast_message(self, event: MessageSentEvent) -> None:
        """Broadcast new message to channel subscribers"""
        # Implementation would use WebSocket manager to broadcast
        pass
    
    async def _broadcast_status_change(self, event: OnlineStatusChangedEvent) -> None:
        """Broadcast status change to all relevant users"""
        # Implementation would use WebSocket manager to broadcast
        pass
    
    async def _broadcast_typing_indicator(self, event: TypingStartedEvent) -> None:
        """Broadcast typing indicator to channel subscribers"""
        # Implementation would use WebSocket manager to broadcast
        pass
    
    async def _broadcast_reaction(self, event: ReactionAddedEvent) -> None:
        """Broadcast reaction to message subscribers"""
        # Implementation would use WebSocket manager to broadcast
        pass

# ================================
# Event Dispatcher
# ================================

class ChatEventDispatcher:
    """Central dispatcher for chat events"""
    
    def __init__(self):
        self.listeners: List[ChatEventListener] = []
        self._setup_default_listeners()
    
    def _setup_default_listeners(self) -> None:
        """Setup default event listeners"""
        self.listeners.extend([
            NotificationEventListener(),
            AnalyticsEventListener(),
            AuditLogEventListener(),
            # WebSocketEventListener() would be added with WebSocket manager
        ])
    
    def add_listener(self, listener: ChatEventListener) -> None:
        """Add an event listener"""
        if listener not in self.listeners:
            self.listeners.append(listener)
            logger.info(f"Added event listener: {listener.__class__.__name__}")
    
    def remove_listener(self, listener: ChatEventListener) -> None:
        """Remove an event listener"""
        if listener in self.listeners:
            self.listeners.remove(listener)
            logger.info(f"Removed event listener: {listener.__class__.__name__}")
    
    async def dispatch(self, event: BaseChatEvent) -> None:
        """Dispatch an event to all listeners"""
        try:
            logger.info(f"Dispatching event: {event.get_event_type()}")
            
            # Dispatch to all listeners concurrently
            tasks = [
                listener.handle_event(event) 
                for listener in self.listeners
            ]
            
            if tasks:
                # Use asyncio.gather with return_exceptions=True to prevent one failure from stopping others
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log any exceptions
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        listener_name = self.listeners[i].__class__.__name__
                        logger.error(f"Listener {listener_name} failed to handle event {event.get_event_type()}: {str(result)}")
            
            logger.debug(f"Event dispatched successfully: {event.get_event_type()}")
            
        except Exception as e:
            logger.error(f"Failed to dispatch event {event.get_event_type()}: {str(e)}")
    
    def get_listener_count(self) -> int:
        """Get the number of registered listeners"""
        return len(self.listeners)
    
    def get_listeners_by_type(self, listener_type: type) -> List[ChatEventListener]:
        """Get listeners of a specific type"""
        return [listener for listener in self.listeners if isinstance(listener, listener_type)]

# ================================
# Event Factory
# ================================

class ChatEventFactory:
    """Factory for creating chat events"""
    
    @staticmethod
    def create_channel_event(
        event_type: str,
        channel_id: UUID,
        channel_name: str,
        user_id: UUID,
        **kwargs
    ) -> BaseChatEvent:
        """Create a channel-related event"""
        timestamp = datetime.utcnow()
        
        if event_type == "created":
            return ChannelCreatedEvent(
                channel_id=channel_id,
                channel_name=channel_name,
                channel_type=kwargs.get('channel_type', 'general'),
                created_by=user_id,
                project_id=kwargs.get('project_id'),
                timestamp=timestamp
            )
        elif event_type == "updated":
            return ChannelUpdatedEvent(
                channel_id=channel_id,
                channel_name=channel_name,
                updated_by=user_id,
                changes=kwargs.get('changes', {}),
                timestamp=timestamp
            )
        elif event_type == "deleted":
            return ChannelDeletedEvent(
                channel_id=channel_id,
                channel_name=channel_name,
                deleted_by=user_id,
                hard_delete=kwargs.get('hard_delete', False),
                timestamp=timestamp
            )
        else:
            raise ValueError(f"Unknown channel event type: {event_type}")
    
    @staticmethod
    def create_message_event(
        event_type: str,
        message_id: UUID,
        channel_id: UUID,
        user_id: UUID,
        **kwargs
    ) -> BaseChatEvent:
        """Create a message-related event"""
        timestamp = datetime.utcnow()
        
        if event_type == "sent":
            return MessageSentEvent(
                message_id=message_id,
                channel_id=channel_id,
                sender_id=user_id,
                content=kwargs.get('content', ''),
                message_type=kwargs.get('message_type', 'text'),
                mentioned_users=kwargs.get('mentioned_users', []),
                parent_message_id=kwargs.get('parent_message_id'),
                timestamp=timestamp
            )
        elif event_type == "updated":
            return MessageUpdatedEvent(
                message_id=message_id,
                channel_id=channel_id,
                updated_by=user_id,
                changes=kwargs.get('changes', {}),
                timestamp=timestamp
            )
        elif event_type == "deleted":
            return MessageDeletedEvent(
                message_id=message_id,
                channel_id=channel_id,
                deleted_by=user_id,
                hard_delete=kwargs.get('hard_delete', False),
                timestamp=timestamp
            )
        else:
            raise ValueError(f"Unknown message event type: {event_type}")

# Global event dispatcher instance
chat_event_dispatcher = ChatEventDispatcher()

