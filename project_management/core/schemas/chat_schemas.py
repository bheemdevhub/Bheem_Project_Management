# app/modules/project_management/core/schemas/chat_schemas.py
"""
Chat and Collaboration Schemas for Project Management Module
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
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

# ================================
# Chat Channel Schemas
# ================================

class ChatChannelBase(BaseModel):
    """Base schema for chat channels"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    channel_type: ChannelType = ChannelType.GENERAL
    is_private: bool = False
    project_id: Optional[UUID] = None

class ChatChannelCreate(ChatChannelBase):
    """Schema for creating a chat channel"""
    member_ids: Optional[List[UUID]] = Field(default_factory=list)

    @validator('member_ids')
    def validate_member_ids(cls, v):
        if v and len(v) > 100:  # Reasonable limit
            raise ValueError('Cannot add more than 100 members at once')
        return v

class ChatChannelUpdate(BaseModel):
    """Schema for updating a chat channel"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_private: Optional[bool] = None
    is_archived: Optional[bool] = None

class ChatChannelResponse(ChatChannelBase):
    """Schema for chat channel response"""
    id: UUID
    created_by: UUID
    is_archived: bool
    member_count: int
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ChatChannelDetailResponse(ChatChannelResponse):
    """Detailed schema for chat channel with members and recent messages"""
    members: List['ChatMemberResponse'] = []
    recent_messages: List['ChatMessageResponse'] = []

# ================================
# Chat Member Schemas
# ================================

class ChatMemberBase(BaseModel):
    """Base schema for chat members"""
    channel_id: UUID
    employee_id: UUID
    role: MemberRole = MemberRole.MEMBER

class ChatMemberCreate(ChatMemberBase):
    """Schema for adding a member to a channel"""
    pass

class ChatMemberUpdate(BaseModel):
    """Schema for updating a chat member"""
    role: Optional[MemberRole] = None

class ChatMemberResponse(ChatMemberBase):
    """Schema for chat member response"""
    id: UUID
    joined_at: datetime
    last_read_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ================================
# Chat Message Schemas
# ================================

class ChatMessageBase(BaseModel):
    """Base schema for chat messages"""
    content: str = Field(..., min_length=1, max_length=4000)
    message_type: MessageType = MessageType.TEXT
    mentioned_users: Optional[List[UUID]] = Field(default_factory=list)
    attachments: Optional[Dict[str, Any]] = None

class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a chat message"""
    channel_id: UUID
    parent_message_id: Optional[UUID] = None

    @validator('content')
    def validate_content(cls, v, values):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class ChatMessageUpdate(BaseModel):
    """Schema for updating a chat message"""
    content: str = Field(..., min_length=1, max_length=4000)

    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class ChatMessageResponse(ChatMessageBase):
    """Schema for chat message response"""
    id: UUID
    channel_id: UUID
    sender_id: UUID
    parent_message_id: Optional[UUID]
    thread_count: int
    is_edited: bool
    is_pinned: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Include reactions
    reactions: List['MessageReactionResponse'] = []

    class Config:
        from_attributes = True

class ChatMessageDetailResponse(ChatMessageResponse):
    """Detailed schema for chat message with thread replies"""
    replies: List['ChatMessageResponse'] = []

# ================================
# Message Reaction Schemas
# ================================

class MessageReactionBase(BaseModel):
    """Base schema for message reactions"""
    emoji: str = Field(..., min_length=1, max_length=50)

class MessageReactionCreate(MessageReactionBase):
    """Schema for creating a message reaction"""
    message_id: UUID

class MessageReactionResponse(MessageReactionBase):
    """Schema for message reaction response"""
    id: UUID
    message_id: UUID
    employee_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# ================================
# Direct Message Schemas
# ================================

class DirectMessageBase(BaseModel):
    """Base schema for direct messages"""
    content: str = Field(..., min_length=1, max_length=4000)
    message_type: MessageType = MessageType.TEXT
    attachments: Optional[Dict[str, Any]] = None

class DirectMessageCreate(DirectMessageBase):
    """Schema for creating a direct message"""
    recipient_id: UUID

    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class DirectMessageResponse(DirectMessageBase):
    """Schema for direct message response"""
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ================================
# Online Status Schemas
# ================================

class OnlineStatusBase(BaseModel):
    """Base schema for online status"""
    status: OnlineStatusEnum = OnlineStatusEnum.OFFLINE
    custom_status: Optional[str] = Field(None, max_length=255)

class OnlineStatusUpdate(OnlineStatusBase):
    """Schema for updating online status"""
    pass

class OnlineStatusResponse(OnlineStatusBase):
    """Schema for online status response"""
    id: UUID
    employee_id: UUID
    last_seen: datetime
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ================================
# Pagination and Filter Schemas
# ================================

class ChatChannelPaginatedResponse(BaseModel):
    """Paginated response for chat channels"""
    items: List[ChatChannelResponse]
    total: int
    page: int
    size: int
    pages: int

class ChatMessagePaginatedResponse(BaseModel):
    """Paginated response for chat messages"""
    items: List[ChatMessageResponse]
    total: int
    page: int
    size: int
    pages: int

class DirectMessagePaginatedResponse(BaseModel):
    """Paginated response for direct messages"""
    items: List[DirectMessageResponse]
    total: int
    page: int
    size: int
    pages: int

class ChatChannelFilterParams(BaseModel):
    """Filter parameters for chat channels"""
    channel_type: Optional[ChannelType] = None
    is_private: Optional[bool] = None
    is_archived: Optional[bool] = None
    project_id: Optional[UUID] = None
    created_by: Optional[UUID] = None

class ChatMessageFilterParams(BaseModel):
    """Filter parameters for chat messages"""
    message_type: Optional[MessageType] = None
    sender_id: Optional[UUID] = None
    has_attachments: Optional[bool] = None
    is_pinned: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

# ================================
# Bulk Operations Schemas
# ================================

class BulkMemberAddRequest(BaseModel):
    """Schema for bulk adding members to a channel"""
    employee_ids: List[UUID] = Field(..., min_items=1, max_items=50)
    role: MemberRole = MemberRole.MEMBER

class BulkMemberRemoveRequest(BaseModel):
    """Schema for bulk removing members from a channel"""
    employee_ids: List[UUID] = Field(..., min_items=1, max_items=50)

class BulkOperationResponse(BaseModel):
    """Response for bulk operations"""
    success_count: int
    failed_count: int
    errors: List[str] = []

# Update forward references
ChatChannelDetailResponse.model_rebuild()
ChatMessageDetailResponse.model_rebuild()

