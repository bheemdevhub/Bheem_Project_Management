"""
Event system for ChatChannel lifecycle
"""
from app.modules.project_management.core.models.project_models import ChatChannel
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def channel_created(channel: ChatChannel):
    logger.info(f"Channel created: {channel.id} ({channel.name})")
    # Add event bus publishing, notification, websocket, etc.

async def channel_updated(channel: ChatChannel, updated_by: UUID):
    logger.info(f"Channel updated: {channel.id} by {updated_by}")
    # Add event bus publishing, notification, websocket, etc.

async def channel_deleted(channel: ChatChannel, deleted_by: UUID):
    logger.info(f"Channel deleted: {channel.id} by {deleted_by}")
    # Add event bus publishing, notification, websocket, etc.

async def channel_archived(channel: ChatChannel, archived_by: UUID):
    logger.info(f"Channel archived: {channel.id} by {archived_by}")
    # Add event bus publishing, notification, websocket, etc.
