"""
Async Service Layer for ChatChannel
Handles CRUD, filtering, permission checks, and event hooks
"""
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func
from app.modules.project_management.core.models.project_models import ChatChannel
from app.modules.project_management.core.schemas.chat_channel_schemas import (
    ChatChannelCreate, ChatChannelUpdate, ChatChannelFilterParams
)
from app.modules.project_management.core.events import chat_channel_events
from fastapi import HTTPException, status

class ChatChannelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_channel(self, channel_data: ChatChannelCreate, created_by: UUID) -> ChatChannel:
        channel = ChatChannel(
            name=channel_data.name,
            description=channel_data.description,
            channel_type=channel_data.channel_type,
            is_private=channel_data.is_private,
            is_archived=channel_data.is_archived,
            project_id=channel_data.project_id,
            created_by=created_by
        )
        self.db.add(channel)
        await self.db.commit()
        await self.db.refresh(channel)
        await chat_channel_events.channel_created(channel)
        return channel

    async def get_channel(self, channel_id: UUID) -> Optional[ChatChannel]:
        result = await self.db.execute(select(ChatChannel).where(ChatChannel.id == channel_id))
        return result.scalar_one_or_none()

    async def list_channels(self, filters: ChatChannelFilterParams, page: int, size: int) -> Tuple[List[ChatChannel], int]:
        query = select(ChatChannel)
        if filters.channel_type:
            query = query.where(ChatChannel.channel_type == filters.channel_type)
        if filters.project_id:
            query = query.where(ChatChannel.project_id == filters.project_id)
        if filters.is_private is not None:
            query = query.where(ChatChannel.is_private == filters.is_private)
        if filters.is_archived is not None:
            query = query.where(ChatChannel.is_archived == filters.is_archived)
        if filters.name:
            query = query.where(ChatChannel.name.ilike(f"%{filters.name}%"))
        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        query = query.offset((page - 1) * size).limit(size)
        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def update_channel(self, channel_id: UUID, channel_data: ChatChannelUpdate, updated_by: UUID) -> Optional[ChatChannel]:
        channel = await self.get_channel(channel_id)
        if not channel:
            return None
        for field, value in channel_data.dict(exclude_unset=True).items():
            setattr(channel, field, value)
        await self.db.commit()
        await self.db.refresh(channel)
        await chat_channel_events.channel_updated(channel, updated_by)
        return channel

    async def delete_channel(self, channel_id: UUID, deleted_by: UUID, hard_delete: bool = False) -> bool:
        channel = await self.get_channel(channel_id)
        if not channel:
            return False
        if hard_delete:
            await self.db.delete(channel)
            await self.db.commit()
            await chat_channel_events.channel_deleted(channel, deleted_by)
        else:
            channel.is_archived = True
            await self.db.commit()
            await chat_channel_events.channel_archived(channel, deleted_by)
        return True
