# app/modules/project_management/core/schemas/chat_schemas.py
"""
Enhanced Chat and Collaboration Schemas for Project Management Module
Comprehensive schemas for all chat-related functionality with validation
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
from uuid import UUID
from enum import Enum

# ================================
# Enums
# ================================

class ChannelType(str, Enum):
    """Types of chat channels"""
    PROJECT = "project"
    TEAM = "team"
    DIRECT = "direct"
    GENERAL = "general"

class MessageType(str, Enum):
    """Types of messages"""
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    SYSTEM = "system"
    ANNOUNCEMENT = "announcement"

class MemberRole(str, Enum):
    """Chat member roles"""
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"

class OnlineStatusEnum(str, Enum):
    """Online status options"""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"

class MessageStatus(str, Enum):
    """Message status options"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    DELETED = "deleted"

# ================================
# Base Schemas
# ================================

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# ================================
# Chat Channel Schemas
# ================================

class ChatChannelBase(BaseModel):
    """Base schema for chat channels"""
    name: str = Field(..., min_length=1, max_length=255, description="Channel name")
    description: Optional[str] = Field(None, max_length=1000, description="Channel description")
    channel_type: ChannelType = Field(default=ChannelType.GENERAL, description="Type of channel")
    is_private: bool = Field(default=False, description="Whether channel is private")
    project_id: Optional[UUID] = Field(None, description="Associated project ID")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Channel name cannot be empty')
        return v.strip()

class ChatChannelCreate(ChatChannelBase):
    """Schema for creating a chat channel"""
    pass

class ChatChannelUpdate(BaseModel):
    """Schema for updating a chat channel"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_private: Optional[bool] = None
    is_archived: Optional[bool] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Channel name cannot be empty')
        return v.strip() if v else v

class ChatChannelInDB(ChatChannelBase, TimestampMixin):
    """Database representation of chat channel"""
    id: UUID
    is_archived: bool = False
    created_by: UUID
    member_count: int = 0
    last_message_at: Optional[datetime] = None

class ChatChannelResponse(ChatChannelInDB):
    """Response schema for chat channel"""
    
    class Config:
        from_attributes = True

class ChatChannelDetailResponse(ChatChannelResponse):
    """Detailed response schema for chat channel with members"""
    members: List['ChatMemberResponse'] = []
    recent_messages: List['ChatMessageResponse'] = []

class ChatChannelPaginatedResponse(BaseModel):
    """Paginated response for chat channels"""
    items: List[ChatChannelResponse]
    total: int
    page: int
    size: int
    pages: int

class ChatChannelFilterParams(BaseModel):
    """Filter parameters for chat channels"""
    channel_type: Optional[ChannelType] = None
    project_id: Optional[UUID] = None
    is_private: Optional[bool] = None
    is_archived: Optional[bool] = None
    member_id: Optional[UUID] = None

# ================================
# Chat Member Schemas
# ================================

class ChatMemberBase(BaseModel):
    """Base schema for chat members"""
    role: MemberRole = Field(default=MemberRole.MEMBER, description="Member role in channel")

class ChatMemberCreate(ChatMemberBase):
    """Schema for adding a member to a channel"""
    channel_id: UUID = Field(..., description="Channel ID")
    employee_id: UUID = Field(..., description="Employee ID")

class ChatMemberUpdate(BaseModel):
    """Schema for updating a chat member"""
    role: Optional[MemberRole] = None
    is_active: Optional[bool] = None

class ChatMemberInDB(ChatMemberBase, TimestampMixin):
    """Database representation of chat member"""
    id: UUID
    channel_id: UUID
    employee_id: UUID
    joined_at: datetime
    last_read_at: Optional[datetime] = None
    is_active: bool = True

class ChatMemberResponse(ChatMemberInDB):
    """Response schema for chat member"""
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    
    class Config:
        from_attributes = True

class BulkMemberAddRequest(BaseModel):
    """Schema for bulk adding members to a channel"""
    channel_id: UUID = Field(..., description="Channel ID")
    employee_ids: List[UUID] = Field(..., min_items=1, max_items=100, description="Employee IDs to add")
    role: MemberRole = Field(default=MemberRole.MEMBER, description="Role to assign to all members")

class BulkMemberRemoveRequest(BaseModel):
    """Schema for bulk removing members from a channel"""
    channel_id: UUID = Field(..., description="Channel ID")
    employee_ids: List[UUID] = Field(..., min_items=1, max_items=100, description="Employee IDs to remove")

class BulkOperationResponse(BaseModel):
    """Response schema for bulk operations"""
    successful: List[UUID] = Field(default_factory=list)
    failed: List[Dict[str, Any]] = Field(default_factory=list)
    total_processed: int = 0
    success_count: int = 0
    failure_count: int = 0

# ================================
# Chat Message Schemas
# ================================

class ChatMessageBase(BaseModel):
    """Base schema for chat messages"""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    mentioned_users: Optional[List[UUID]] = Field(default_factory=list, description="Mentioned user IDs")
    attachments: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Message attachments")

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a chat message"""
    channel_id: UUID = Field(..., description="Channel ID")
    parent_message_id: Optional[UUID] = Field(None, description="Parent message ID for replies")

class ChatMessageUpdate(BaseModel):
    """Schema for updating a chat message"""
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    is_pinned: Optional[bool] = None

    @validator('content')
    def validate_content(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip() if v else v

class ChatMessageInDB(ChatMessageBase, TimestampMixin):
    """Database representation of chat message"""
    id: UUID
    channel_id: UUID
    sender_id: UUID
    parent_message_id: Optional[UUID] = None
    thread_count: int = 0
    is_edited: bool = False
    is_pinned: bool = False
    message_status: MessageStatus = MessageStatus.SENT

class ChatMessageResponse(ChatMessageInDB):
    """Response schema for chat message"""
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    reaction_count: int = 0
    user_reaction: Optional[str] = None
    
    class Config:
        from_attributes = True

class ChatMessageDetailResponse(ChatMessageResponse):
    """Detailed response schema for chat message"""
    reactions: List['MessageReactionResponse'] = []
    replies: List['ChatMessageResponse'] = []

class ChatMessagePaginatedResponse(BaseModel):
    """Paginated response for chat messages"""
    items: List[ChatMessageResponse]
    total: int
    page: int
    size: int
    pages: int

class ChatMessageFilterParams(BaseModel):
    """Filter parameters for chat messages"""
    message_type: Optional[MessageType] = None
    sender_id: Optional[UUID] = None
    parent_message_id: Optional[UUID] = None
    is_pinned: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search_query: Optional[str] = None

# ================================
# Message Reaction Schemas
# ================================

class MessageReactionBase(BaseModel):
    """Base schema for message reactions"""
    emoji: str = Field(..., min_length=1, max_length=50, description="Emoji reaction")

    @validator('emoji')
    def validate_emoji(cls, v):
        if not v.strip():
            raise ValueError('Emoji cannot be empty')
        return v.strip()

class MessageReactionCreate(MessageReactionBase):
    """Schema for creating a message reaction"""
    message_id: UUID = Field(..., description="Message ID")

class MessageReactionInDB(MessageReactionBase, TimestampMixin):
    """Database representation of message reaction"""
    id: UUID
    message_id: UUID
    employee_id: UUID

class MessageReactionResponse(MessageReactionInDB):
    """Response schema for message reaction"""
    employee_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class ReactionSummary(BaseModel):
    """Summary of reactions for a message"""
    emoji: str
    count: int
    users: List[str] = []

# ================================
# Direct Message Schemas
# ================================

class DirectMessageBase(BaseModel):
    """Base schema for direct messages"""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    attachments: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Message attachments")

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class DirectMessageCreate(DirectMessageBase):
    """Schema for creating a direct message"""
    recipient_id: UUID = Field(..., description="Recipient employee ID")

class DirectMessageInDB(DirectMessageBase, TimestampMixin):
    """Database representation of direct message"""
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    is_read: bool = False
    read_at: Optional[datetime] = None

class DirectMessageResponse(DirectMessageInDB):
    """Response schema for direct message"""
    sender_name: Optional[str] = None
    recipient_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class DirectMessagePaginatedResponse(BaseModel):
    """Paginated response for direct messages"""
    items: List[DirectMessageResponse]
    total: int
    page: int
    size: int
    pages: int

class ConversationResponse(BaseModel):
    """Response schema for conversation summary"""
    participant_id: UUID
    participant_name: str
    last_message: Optional[DirectMessageResponse] = None
    unread_count: int = 0

# ================================
# Online Status Schemas
# ================================

class OnlineStatusBase(BaseModel):
    """Base schema for online status"""
    status: OnlineStatusEnum = Field(default=OnlineStatusEnum.OFFLINE, description="Online status")
    custom_status: Optional[str] = Field(None, max_length=255, description="Custom status message")

class OnlineStatusUpdate(OnlineStatusBase):
    """Schema for updating online status"""
    pass

class OnlineStatusInDB(OnlineStatusBase, TimestampMixin):
    """Database representation of online status"""
    id: UUID
    employee_id: UUID
    last_seen: datetime

class OnlineStatusResponse(OnlineStatusInDB):
    """Response schema for online status"""
    employee_name: Optional[str] = None
    
    class Config:
        from_attributes = True

# ================================
# Statistics and Analytics Schemas
# ================================

class ChannelStatistics(BaseModel):
    """Channel statistics schema"""
    total_messages: int = 0
    total_members: int = 0
    active_members_today: int = 0
    messages_today: int = 0
    most_active_member: Optional[str] = None

class UserChatStatistics(BaseModel):
    """User chat statistics schema"""
    total_channels: int = 0
    total_messages_sent: int = 0
    total_reactions_given: int = 0
    total_direct_messages: int = 0
    average_response_time_minutes: Optional[float] = None

class ChatAnalyticsResponse(BaseModel):
    """Chat analytics response schema"""
    total_channels: int = 0
    total_messages: int = 0
    total_active_users: int = 0
    messages_by_hour: List[Dict[str, Any]] = []
    top_channels: List[Dict[str, Any]] = []
    user_activity: List[Dict[str, Any]] = []

# ================================
# WebSocket Schemas
# ================================

class WebSocketMessage(BaseModel):
    """WebSocket message schema"""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class TypingIndicator(BaseModel):
    """Typing indicator schema"""
    channel_id: UUID
    user_id: UUID
    user_name: str
    is_typing: bool

class OnlineStatusBroadcast(BaseModel):
    """Online status broadcast schema"""
    user_id: UUID
    user_name: str
    status: OnlineStatusEnum
    custom_status: Optional[str] = None

# ================================
# Search and Filter Schemas
# ================================

class MessageSearchRequest(BaseModel):
    """Message search request schema"""
    query: str = Field(..., min_length=1, max_length=500)
    channel_ids: Optional[List[UUID]] = None
    sender_ids: Optional[List[UUID]] = None
    message_types: Optional[List[MessageType]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    include_archived: bool = False

class MessageSearchResponse(BaseModel):
    """Message search response schema"""
    messages: List[ChatMessageResponse]
    total: int
    query: str
    highlights: List[str] = []

# Update forward references
ChatChannelDetailResponse.model_rebuild()
ChatMessageDetailResponse.model_rebuild()
