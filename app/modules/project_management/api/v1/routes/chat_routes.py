# app/modules/project_management/api/v1/routes/chat_routes.py
"""
Chat and Collaboration API Routes for Project Management Module
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from app.core.database import get_db
from app.modules.auth.core.services.permissions_service import (
    require_roles, require_api_permission, get_current_user_id, get_current_company_id
)
from app.shared.models import UserRole
from app.modules.project_management.core.services.chat_service import ChatService
from app.modules.project_management.core.schemas.chat_schemas import (
    # Channel schemas
    ChatChannelCreate, ChatChannelUpdate, ChatChannelResponse, 
    ChatChannelDetailResponse, ChatChannelPaginatedResponse, ChatChannelFilterParams,
    # Member schemas
    ChatMemberCreate, ChatMemberUpdate, ChatMemberResponse,
    BulkMemberAddRequest, BulkMemberRemoveRequest, BulkOperationResponse,
    # Message schemas
    ChatMessageCreate, ChatMessageUpdate, ChatMessageResponse,
    ChatMessageDetailResponse, ChatMessagePaginatedResponse, ChatMessageFilterParams,
    # Reaction schemas
    MessageReactionCreate, MessageReactionResponse,
    # Direct message schemas
    DirectMessageCreate, DirectMessageResponse, DirectMessagePaginatedResponse,
    # Online status schemas
    OnlineStatusUpdate, OnlineStatusResponse,
    # Enums
    ChannelType, MemberRole, MessageType, OnlineStatusEnum
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Project Management - Chat & Collaboration"],
    responses={404: {"description": "Not found"}}
)

# ================================
# Chat Channel Endpoints
# ================================

@router.post("/channels", 
             response_model=ChatChannelResponse, 
             status_code=status.HTTP_201_CREATED,
             dependencies=[
                 Depends(lambda: require_api_permission("project_management.chat.channel.create")),
                 Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
             ])
async def create_chat_channel(
    channel_data: ChatChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create a new chat channel.
    
    Allows users to create chat channels for project communication.
    """
    try:
        chat_service = ChatService(db)
        channel = await chat_service.create_channel(channel_data, current_user_id)
        
        return ChatChannelResponse(
            id=channel.id,
            name=channel.name,
            description=channel.description,
            channel_type=ChannelType(channel.channel_type),
            is_private=channel.is_private,
            project_id=channel.project_id,
            created_by=channel.created_by,
            is_archived=channel.is_archived,
            member_count=1,  # Will be calculated properly in service
            message_count=0,
            last_message_at=None,
            created_at=channel.created_at,
            updated_at=channel.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating channel: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/channels", 
            response_model=ChatChannelPaginatedResponse,
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.channel.read")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE, UserRole.VIEWER]))
            ])
async def list_chat_channels(
    channel_type: Optional[ChannelType] = Query(None, description="Filter by channel type"),
    is_private: Optional[bool] = Query(None, description="Filter by privacy setting"),
    is_archived: Optional[bool] = Query(False, description="Include archived channels"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("updated_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List chat channels accessible to the current user.
    """
    try:
        chat_service = ChatService(db)
        
        filters = ChatChannelFilterParams(
            channel_type=channel_type,
            is_private=is_private,
            is_archived=is_archived,
            project_id=project_id
        )
        
        channels, total = await chat_service.list_channels(
            user_id=current_user_id,
            filters=filters,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_desc=sort_desc
        )
        
        channel_responses = [
            ChatChannelResponse(
                id=channel.id,
                name=channel.name,
                description=channel.description,
                channel_type=ChannelType(channel.channel_type),
                is_private=channel.is_private,
                project_id=channel.project_id,
                created_by=channel.created_by,
                is_archived=channel.is_archived,
                member_count=len(channel.members) if hasattr(channel, 'members') else 0,
                message_count=channel.message_count or 0,
                last_message_at=channel.last_message_at,
                created_at=channel.created_at,
                updated_at=channel.updated_at
            ) for channel in channels
        ]
        
        pages = (total + size - 1) // size
        
        return ChatChannelPaginatedResponse(
            items=channel_responses,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error listing channels: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/channels/{channel_id}", 
            response_model=ChatChannelDetailResponse,
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.channel.read")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE, UserRole.VIEWER]))
            ])
async def get_chat_channel(
    channel_id: UUID = Path(..., description="Channel ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get detailed information about a specific chat channel.
    """
    try:
        chat_service = ChatService(db)
        channel = await chat_service.get_channel_by_id(channel_id)
        
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
        
        # TODO: Add proper member and message loading
        return ChatChannelDetailResponse(
            id=channel.id,
            name=channel.name,
            description=channel.description,
            channel_type=ChannelType(channel.channel_type),
            is_private=channel.is_private,
            project_id=channel.project_id,
            created_by=channel.created_by,
            is_archived=channel.is_archived,
            member_count=len(channel.members) if hasattr(channel, 'members') else 0,
            message_count=channel.message_count or 0,
            last_message_at=channel.last_message_at,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
            members=[],  # Will be populated properly in service
            recent_messages=[]  # Will be populated properly in service
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.put("/channels/{channel_id}", 
            response_model=ChatChannelResponse,
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.channel.update")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
            ])
async def update_chat_channel(
    channel_id: UUID = Path(..., description="Channel ID"),
    channel_data: ChatChannelUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update a chat channel (admin/moderator only).
    """
    try:
        chat_service = ChatService(db)
        channel = await chat_service.update_channel(channel_id, channel_data, current_user_id)
        
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
        
        return ChatChannelResponse(
            id=channel.id,
            name=channel.name,
            description=channel.description,
            channel_type=ChannelType(channel.channel_type),
            is_private=channel.is_private,
            project_id=channel.project_id,
            created_by=channel.created_by,
            is_archived=channel.is_archived,
            member_count=len(channel.members) if hasattr(channel, 'members') else 0,
            message_count=channel.message_count or 0,
            last_message_at=channel.last_message_at,
            created_at=channel.created_at,
            updated_at=channel.updated_at
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.delete("/channels/{channel_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[
                   Depends(lambda: require_api_permission("project_management.chat.channel.delete")),
                   Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER]))
               ])
async def delete_chat_channel(
    channel_id: UUID = Path(..., description="Channel ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete a chat channel (admin only).
    """
    try:
        chat_service = ChatService(db)
        success = await chat_service.delete_channel(channel_id, current_user_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# ================================
# Chat Member Endpoints
# ================================

@router.post("/channels/{channel_id}/members", 
             response_model=ChatMemberResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[
                 Depends(lambda: require_api_permission("project_management.chat.member.create")),
                 Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
             ])
async def add_channel_member(
    channel_id: UUID = Path(..., description="Channel ID"),
    member_data: ChatMemberCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Add a member to a chat channel.
    """
    try:
        # Ensure the channel_id in the path matches the one in the body
        member_data.channel_id = channel_id
        
        chat_service = ChatService(db)
        member = await chat_service.add_member(channel_id, member_data, current_user_id)
        
        return ChatMemberResponse(
            id=member.id,
            channel_id=member.channel_id,
            employee_id=member.employee_id,
            role=MemberRole(member.role),
            joined_at=member.joined_at,
            last_read_at=member.last_read_at,
            is_active=member.is_active,
            created_at=member.created_at
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding member to channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.delete("/channels/{channel_id}/members/{employee_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[
                   Depends(lambda: require_api_permission("project_management.chat.member.delete")),
                   Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
               ])
async def remove_channel_member(
    channel_id: UUID = Path(..., description="Channel ID"),
    employee_id: UUID = Path(..., description="Employee ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Remove a member from a chat channel.
    """
    try:
        chat_service = ChatService(db)
        success = await chat_service.remove_member(channel_id, employee_id, current_user_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing member from channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.post("/channels/{channel_id}/members/bulk-add", 
             response_model=BulkOperationResponse,
             dependencies=[
                 Depends(lambda: require_api_permission("project_management.chat.member.create")),
                 Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER]))
             ])
async def bulk_add_channel_members(
    channel_id: UUID = Path(..., description="Channel ID"),
    request: BulkMemberAddRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Bulk add members to a chat channel.
    """
    try:
        chat_service = ChatService(db)
        result = await chat_service.bulk_add_members(channel_id, request, current_user_id)
        
        return BulkOperationResponse(
            success_count=result["success_count"],
            failed_count=result["failed_count"],
            errors=result["errors"]
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error bulk adding members to channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# ================================
# Chat Message Endpoints
# ================================

@router.post("/channels/{channel_id}/messages", 
             response_model=ChatMessageResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[
                 Depends(lambda: require_api_permission("project_management.chat.message.create")),
                 Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
             ])
async def send_message(
    channel_id: UUID = Path(..., description="Channel ID"),
    message_data: ChatMessageCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Send a message to a chat channel.
    """
    try:
        # Ensure the channel_id in the path matches the one in the body
        message_data.channel_id = channel_id
        
        chat_service = ChatService(db)
        message = await chat_service.send_message(message_data, current_user_id)
        
        return ChatMessageResponse(
            id=message.id,
            content=message.content,
            message_type=MessageType(message.message_type),
            mentioned_users=message.mentioned_users or [],
            attachments=message.attachments,
            channel_id=message.channel_id,
            sender_id=message.sender_id,
            parent_message_id=message.parent_message_id,
            thread_count=message.thread_count,
            is_edited=message.is_edited,
            is_pinned=message.is_pinned,
            created_at=message.created_at,
            updated_at=message.updated_at,
            reactions=[]  # Will be populated properly
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending message to channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/channels/{channel_id}/messages", 
            response_model=ChatMessagePaginatedResponse,
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.message.read")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE, UserRole.VIEWER]))
            ])
async def get_channel_messages(
    channel_id: UUID = Path(..., description="Channel ID"),
    message_type: Optional[MessageType] = Query(None, description="Filter by message type"),
    sender_id: Optional[UUID] = Query(None, description="Filter by sender"),
    is_pinned: Optional[bool] = Query(None, description="Filter by pinned status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    sort_desc: bool = Query(True, description="Sort by creation time descending"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get messages from a chat channel.
    """
    try:
        chat_service = ChatService(db)
        
        filters = ChatMessageFilterParams(
            message_type=message_type,
            sender_id=sender_id,
            is_pinned=is_pinned
        )
        
        messages, total = await chat_service.get_channel_messages(
            channel_id=channel_id,
            user_id=current_user_id,
            filters=filters,
            page=page,
            size=size,
            sort_desc=sort_desc
        )
        
        message_responses = [
            ChatMessageResponse(
                id=message.id,
                content=message.content,
                message_type=MessageType(message.message_type),
                mentioned_users=message.mentioned_users or [],
                attachments=message.attachments,
                channel_id=message.channel_id,
                sender_id=message.sender_id,
                parent_message_id=message.parent_message_id,
                thread_count=message.thread_count,
                is_edited=message.is_edited,
                is_pinned=message.is_pinned,
                created_at=message.created_at,
                updated_at=message.updated_at,
                reactions=[]  # Will be populated properly
            ) for message in messages
        ]
        
        pages = (total + size - 1) // size
        
        return ChatMessagePaginatedResponse(
            items=message_responses,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting messages for channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.put("/messages/{message_id}", 
            response_model=ChatMessageResponse,
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.message.update")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
            ])
async def update_message(
    message_id: UUID = Path(..., description="Message ID"),
    message_data: ChatMessageUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update a chat message (own messages only).
    """
    try:
        chat_service = ChatService(db)
        message = await chat_service.update_message(message_id, message_data, current_user_id)
        
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        
        return ChatMessageResponse(
            id=message.id,
            content=message.content,
            message_type=MessageType(message.message_type),
            mentioned_users=message.mentioned_users or [],
            attachments=message.attachments,
            channel_id=message.channel_id,
            sender_id=message.sender_id,
            parent_message_id=message.parent_message_id,
            thread_count=message.thread_count,
            is_edited=message.is_edited,
            is_pinned=message.is_pinned,
            created_at=message.created_at,
            updated_at=message.updated_at,
            reactions=[]
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating message {message_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.delete("/messages/{message_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[
                   Depends(lambda: require_api_permission("project_management.chat.message.delete")),
                   Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
               ])
async def delete_message(
    message_id: UUID = Path(..., description="Message ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete a chat message.
    """
    try:
        chat_service = ChatService(db)
        success = await chat_service.delete_message(message_id, current_user_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# ================================
# Message Reaction Endpoints
# ================================

@router.post("/messages/{message_id}/reactions", 
             response_model=MessageReactionResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[
                 Depends(lambda: require_api_permission("project_management.chat.reaction.create")),
                 Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
             ])
async def add_message_reaction(
    message_id: UUID = Path(..., description="Message ID"),
    reaction_data: MessageReactionCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Add a reaction to a message.
    """
    try:
        # Ensure the message_id in the path matches the one in the body
        reaction_data.message_id = message_id
        
        chat_service = ChatService(db)
        reaction = await chat_service.add_reaction(reaction_data, current_user_id)
        
        return MessageReactionResponse(
            id=reaction.id,
            message_id=reaction.message_id,
            employee_id=reaction.employee_id,
            emoji=reaction.emoji,
            created_at=reaction.created_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding reaction to message {message_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.delete("/messages/{message_id}/reactions/{emoji}", 
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[
                   Depends(lambda: require_api_permission("project_management.chat.reaction.delete")),
                   Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
               ])
async def remove_message_reaction(
    message_id: UUID = Path(..., description="Message ID"),
    emoji: str = Path(..., description="Emoji"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Remove a reaction from a message.
    """
    try:
        chat_service = ChatService(db)
        success = await chat_service.remove_reaction(message_id, emoji, current_user_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reaction not found")
        
    except Exception as e:
        logger.error(f"Error removing reaction from message {message_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# ================================
# Direct Message Endpoints
# ================================

@router.post("/direct-messages", 
             response_model=DirectMessageResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[
                 Depends(lambda: require_api_permission("project_management.chat.direct_message.create")),
                 Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
             ])
async def send_direct_message(
    message_data: DirectMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Send a direct message to another user.
    """
    try:
        chat_service = ChatService(db)
        message = await chat_service.send_direct_message(message_data, current_user_id)
        
        return DirectMessageResponse(
            id=message.id,
            content=message.content,
            message_type=MessageType(message.message_type),
            attachments=message.attachments,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            is_read=message.is_read,
            read_at=message.read_at,
            created_at=message.created_at,
            updated_at=message.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending direct message: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/direct-messages/{other_user_id}", 
            response_model=DirectMessagePaginatedResponse,
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.direct_message.read")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
            ])
async def get_direct_messages(
    other_user_id: UUID = Path(..., description="Other user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get direct messages with another user.
    """
    try:
        chat_service = ChatService(db)
        messages, total = await chat_service.get_direct_messages(
            user_id=current_user_id,
            other_user_id=other_user_id,
            page=page,
            size=size
        )
        
        message_responses = [
            DirectMessageResponse(
                id=message.id,
                content=message.content,
                message_type=MessageType(message.message_type),
                attachments=message.attachments,
                sender_id=message.sender_id,
                recipient_id=message.recipient_id,
                is_read=message.is_read,
                read_at=message.read_at,
                created_at=message.created_at,
                updated_at=message.updated_at
            ) for message in messages
        ]
        
        pages = (total + size - 1) // size
        
        return DirectMessagePaginatedResponse(
            items=message_responses,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error getting direct messages: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.put("/direct-messages/{message_id}/read", 
            status_code=status.HTTP_204_NO_CONTENT,
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.direct_message.update")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
            ])
async def mark_direct_message_read(
    message_id: UUID = Path(..., description="Message ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Mark a direct message as read.
    """
    try:
        chat_service = ChatService(db)
        success = await chat_service.mark_direct_message_as_read(message_id, current_user_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# ================================
# Online Status Endpoints
# ================================

@router.put("/online-status", 
            response_model=OnlineStatusResponse,
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.status.update")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE]))
            ])
async def update_online_status(
    status_data: OnlineStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update current user's online status.
    """
    try:
        chat_service = ChatService(db)
        status = await chat_service.update_online_status(current_user_id, status_data)
        
        return OnlineStatusResponse(
            id=status.id,
            employee_id=status.employee_id,
            status=OnlineStatusEnum(status.status),
            custom_status=status.custom_status,
            last_seen=status.last_seen,
            created_at=status.created_at,
            updated_at=status.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error updating online status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/online-users", 
            response_model=List[OnlineStatusResponse],
            dependencies=[
                Depends(lambda: require_api_permission("project_management.chat.status.read")),
                Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.EMPLOYEE, UserRole.VIEWER]))
            ])
async def get_online_users(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of users to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of currently online users.
    """
    try:
        chat_service = ChatService(db)
        statuses = await chat_service.get_online_users(limit)
        
        return [
            OnlineStatusResponse(
                id=status.id,
                employee_id=status.employee_id,
                status=OnlineStatusEnum(status.status),
                custom_status=status.custom_status,
                last_seen=status.last_seen,
                created_at=status.created_at,
                updated_at=status.updated_at
            ) for status in statuses
        ]
        
    except Exception as e:
        logger.error(f"Error getting online users: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# ================================
# WebSocket Endpoint for Real-time Communication
# ================================

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat communication.
    """
    await websocket.accept()
    
    # Add connection to the event handler
    # This would require implementing proper WebSocket connection management
    
    try:
        chat_service = ChatService(db)
        
        # Update user's last seen
        await chat_service.update_last_seen(user_id)
        
        while True:
            # Wait for messages from the client
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                await chat_service.update_last_seen(user_id)
            
            # Add more message type handlers as needed
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        await websocket.close()
