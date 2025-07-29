"""
Pydantic Schemas for ChatChannel API
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, constr

class ChatChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    channel_type: str = Field(..., min_length=1, max_length=50)  # project, team, direct, public
    is_private: bool = False
    is_archived: bool = False
    project_id: Optional[UUID]

class ChatChannelCreate(ChatChannelBase):
    pass

class ChatChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_private: Optional[bool]
    is_archived: Optional[bool]
    channel_type: Optional[str] = Field(None, min_length=1, max_length=50)
    project_id: Optional[UUID]

class ChatChannelResponse(ChatChannelBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    class Config:
        orm_mode = True

class ChatChannelDetailResponse(ChatChannelResponse):
    members: Optional[List[UUID]] = None  # Can be expanded to full member objects
    messages: Optional[List[UUID]] = None  # Can be expanded to full message objects

class ChatChannelPaginatedResponse(BaseModel):
    items: List[ChatChannelResponse]
    total: int
    page: int
    size: int
    pages: int

class ChatChannelFilterParams(BaseModel):
    channel_type: Optional[str]
    project_id: Optional[UUID]
    is_private: Optional[bool]
    is_archived: Optional[bool]
    name: Optional[str]
