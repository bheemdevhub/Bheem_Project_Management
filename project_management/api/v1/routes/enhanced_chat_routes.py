# app/modules/project_management/api/v1/routes/enhanced_chat_routes.py
"""
Enhanced Chat and Collaboration API Routes for Project Management Module
Comprehensive REST APIs with authentication, validation, and best practices
"""
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging
import asyncio
from datetime import datetime, timedelta

from bheem_core.core.database import get_db
from bheem_core.modules.auth.core.services.permissions_service import (
    require_roles, require_api_permission, get_current_user_id, get_current_company_id
)
from bheem_core.shared.models import UserRole
from bheem_core.modules.project_management.core.services.enhanced_chat_service import EnhancedChatService
from bheem_core.modules.project_management.core.services.chat_websocket_manager import chat_websocket_manager
from bheem_core.modules.project_management.core.schemas.enhanced_chat_schemas import (
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
    MessageReactionCreate, MessageReactionResponse, ReactionSummary,
    # Direct message schemas
    DirectMessageCreate, DirectMessageResponse, DirectMessagePaginatedResponse, ConversationResponse,
    # Online status schemas
    OnlineStatusUpdate, OnlineStatusResponse,
    # Statistics schemas
    ChannelStatistics, UserChatStatistics, ChatAnalyticsResponse,
    # Search schemas
    MessageSearchRequest, MessageSearchResponse,
    # WebSocket schemas
    WebSocketMessage, TypingIndicator, OnlineStatusBroadcast,
    # Enums
    ChannelType, MemberRole, MessageType, OnlineStatusEnum
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Project Management - Enhanced Chat & Collaboration"],
    responses={404: {"description": "Not found"}}
)

# ================================
# Chat Channel Endpoints
# ================================

@router.post(
    "/channels",
    response_model=ChatChannelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Chat Channel",
    description="Create a new chat channel with proper authentication and permissions",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.create_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD]))
    ]
)
async def create_chat_channel(
    channel_data: ChatChannelCreate,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatChannelResponse:
    """
    Create a new chat channel.
    
    - **name**: Channel name (required, 1-255 characters)
    - **description**: Channel description (optional, max 1000 characters)
    - **channel_type**: Type of channel (project, team, direct, general)
    - **is_private**: Whether the channel is private (default: False)
    - **project_id**: Associated project ID (optional)
    
    **Permissions Required:**
    - pm.chat.create_channel
    - Role: Admin, Project Manager, or Team Lead
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Create channel
        new_channel = await chat_service.create_channel(
            channel_data=channel_data,
            created_by=current_user_id
        )
        
        logger.info(f"Channel created successfully: {new_channel.id} by user {current_user_id}")
        
        return ChatChannelResponse.from_orm(new_channel)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create channel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create channel"
        )

@router.get(
    "/channels",
    response_model=ChatChannelPaginatedResponse,
    summary="List Chat Channels",
    description="Get paginated list of chat channels with filtering options",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def list_chat_channels(
    channel_type: Optional[ChannelType] = Query(None, description="Filter by channel type"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    is_private: Optional[bool] = Query(None, description="Filter by privacy setting"),
    is_archived: Optional[bool] = Query(False, description="Include archived channels"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatChannelPaginatedResponse:
    """
    List chat channels with filtering and pagination.
    
    **Query Parameters:**
    - **channel_type**: Filter by channel type
    - **project_id**: Filter by associated project
    - **is_private**: Filter by privacy setting
    - **is_archived**: Include archived channels
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **sort_by**: Sort field (default: created_at)
    - **sort_desc**: Sort descending (default: true)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Create filter params
        filters = ChatChannelFilterParams(
            channel_type=channel_type,
            project_id=project_id,
            is_private=is_private,
            is_archived=is_archived
        )
        
        # Get channels
        channels, total = await chat_service.list_channels(
            filters=filters,
            employee_id=current_user_id,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_desc=sort_desc
        )
        
        # Calculate pagination info
        pages = (total + size - 1) // size
        
        return ChatChannelPaginatedResponse(
            items=[ChatChannelResponse.from_orm(channel) for channel in channels],
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Failed to list channels: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list channels"
        )

@router.get(
    "/channels/{channel_id}",
    response_model=ChatChannelDetailResponse,
    summary="Get Chat Channel Details",
    description="Get detailed information about a specific chat channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def get_chat_channel(
    channel_id: UUID = Path(..., description="Channel ID"),
    include_members: bool = Query(True, description="Include channel members"),
    include_recent_messages: bool = Query(False, description="Include recent messages"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatChannelDetailResponse:
    """
    Get detailed information about a chat channel.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    
    **Query Parameters:**
    - **include_members**: Include channel member list
    - **include_recent_messages**: Include recent messages
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Get channel
        channel = await chat_service.get_channel_by_id(
            channel_id=channel_id,
            include_members=include_members,
            include_recent_messages=include_recent_messages
        )
        
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        # TODO: Check if user has access to this channel
        
        # Build response
        response_data = ChatChannelResponse.from_orm(channel)
        
        # Add members if requested
        members = []
        if include_members:
            members_list = await chat_service.get_channel_members(channel_id)
            members = [ChatMemberResponse.from_orm(member) for member in members_list]
        
        # Add recent messages if requested
        recent_messages = []
        if include_recent_messages:
            messages_list, _ = await chat_service.get_channel_messages(
                channel_id=channel_id,
                limit=10,
                offset=0
            )
            recent_messages = [ChatMessageResponse.from_orm(msg) for msg in messages_list]
        
        return ChatChannelDetailResponse(
            **response_data.dict(),
            members=members,
            recent_messages=recent_messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get channel {channel_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get channel"
        )

@router.put(
    "/channels/{channel_id}",
    response_model=ChatChannelResponse,
    summary="Update Chat Channel",
    description="Update chat channel information",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.update_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD]))
    ]
)
async def update_chat_channel(
    channel_id: UUID = Path(..., description="Channel ID"),
    channel_data: ChatChannelUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatChannelResponse:
    """
    Update chat channel information.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    
    **Request Body:**
    - **name**: New channel name (optional)
    - **description**: New channel description (optional)
    - **is_private**: New privacy setting (optional)
    - **is_archived**: New archived status (optional)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Update channel
        updated_channel = await chat_service.update_channel(
            channel_id=channel_id,
            channel_data=channel_data,
            updated_by=current_user_id
        )
        
        if not updated_channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        logger.info(f"Channel updated successfully: {channel_id} by user {current_user_id}")
        
        return ChatChannelResponse.from_orm(updated_channel)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update channel {channel_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update channel"
        )

@router.delete(
    "/channels/{channel_id}",
    response_model=Dict[str, Any],
    summary="Delete Chat Channel",
    description="Delete or archive a chat channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.delete_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER]))
    ]
)
async def delete_chat_channel(
    channel_id: UUID = Path(..., description="Channel ID"),
    hard_delete: bool = Query(False, description="Permanently delete channel"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> Dict[str, Any]:
    """
    Delete or archive a chat channel.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    
    **Query Parameters:**
    - **hard_delete**: If true, permanently delete; if false, soft delete (default: false)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Delete channel
        success = await chat_service.delete_channel(
            channel_id=channel_id,
            deleted_by=current_user_id,
            hard_delete=hard_delete
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        logger.info(f"Channel {'permanently' if hard_delete else 'soft'} deleted: {channel_id}")
        
        return {
            "message": f"Channel {'permanently deleted' if hard_delete else 'archived'} successfully",
            "channel_id": str(channel_id),
            "hard_delete": hard_delete
        }
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete channel {channel_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete channel"
        )

# ================================
# Chat Member Endpoints
# ================================

@router.post(
    "/channels/{channel_id}/members",
    response_model=ChatMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Member to Channel",
    description="Add a member to a chat channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.manage_members")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD]))
    ]
)
async def add_channel_member(
    channel_id: UUID = Path(..., description="Channel ID"),
    member_data: ChatMemberCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatMemberResponse:
    """
    Add a member to a chat channel.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    
    **Request Body:**
    - **employee_id**: ID of employee to add
    - **role**: Role to assign (admin, moderator, member)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Set channel_id from path
        member_data.channel_id = channel_id
        
        # Add member
        new_member = await chat_service.add_member_to_channel(
            member_data=member_data,
            added_by=current_user_id
        )
        
        # Add real-time WebSocket notification
        background_tasks.add_task(
            chat_websocket_manager.handle_member_added,
            channel_id=channel_id,
            member_data=ChatMemberResponse.from_orm(new_member).dict(),
            added_by=current_user_id
        )
        
        logger.info(f"Member {member_data.employee_id} added to channel {channel_id}")
        
        return ChatMemberResponse.from_orm(new_member)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to add member to channel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add member to channel"
        )

@router.get(
    "/channels/{channel_id}/members",
    response_model=List[ChatMemberResponse],
    summary="Get Channel Members",
    description="Get list of channel members",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_members")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def get_channel_members(
    channel_id: UUID = Path(..., description="Channel ID"),
    role_filter: Optional[MemberRole] = Query(None, description="Filter by role"),
    active_only: bool = Query(True, description="Include only active members"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> List[ChatMemberResponse]:
    """
    Get list of channel members.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    
    **Query Parameters:**
    - **role_filter**: Filter by member role
    - **active_only**: Include only active members (default: true)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Get members
        members = await chat_service.get_channel_members(
            channel_id=channel_id,
            role_filter=role_filter,
            active_only=active_only
        )
        
        return [ChatMemberResponse.from_orm(member) for member in members]
        
    except Exception as e:
        logger.error(f"Failed to get channel members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get channel members"
        )

@router.delete(
    "/channels/{channel_id}/members/{employee_id}",
    response_model=Dict[str, Any],
    summary="Remove Member from Channel",
    description="Remove a member from a chat channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.manage_members")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def remove_channel_member(
    channel_id: UUID = Path(..., description="Channel ID"),
    employee_id: UUID = Path(..., description="Employee ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> Dict[str, Any]:
    """
    Remove a member from a chat channel.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    - **employee_id**: Unique identifier of the employee to remove
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Remove member
        success = await chat_service.remove_member_from_channel(
            channel_id=channel_id,
            employee_id=employee_id,
            removed_by=current_user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in channel"
            )
        
        logger.info(f"Member {employee_id} removed from channel {channel_id}")
        
        return {
            "message": "Member removed from channel successfully",
            "channel_id": str(channel_id),
            "employee_id": str(employee_id)
        }
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove member from channel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member from channel"
        )

@router.put(
    "/channels/{channel_id}/members/{employee_id}/role",
    response_model=ChatMemberResponse,
    summary="Update Member Role",
    description="Update a member's role in a chat channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.manage_member_roles")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER]))
    ]
)
async def update_member_role(
    channel_id: UUID = Path(..., description="Channel ID"),
    employee_id: UUID = Path(..., description="Employee ID"),
    new_role: MemberRole = Body(..., embed=True, description="New role"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatMemberResponse:
    """
    Update a member's role in a chat channel.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    - **employee_id**: Unique identifier of the employee
    
    **Request Body:**
    - **new_role**: New role to assign (admin, moderator, member)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Update member role
        updated_member = await chat_service.update_member_role(
            channel_id=channel_id,
            employee_id=employee_id,
            new_role=new_role,
            updated_by=current_user_id
        )
        
        if not updated_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in channel"
            )
        
        logger.info(f"Member {employee_id} role updated to {new_role.value} in channel {channel_id}")
        
        return ChatMemberResponse.from_orm(updated_member)
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update member role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )

# ================================
# Chat Message Endpoints
# ================================

@router.post(
    "/channels/{channel_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Message",
    description="Send a message to a chat channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.send_message")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def send_message(
    channel_id: UUID = Path(..., description="Channel ID"),
    message_data: ChatMessageCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatMessageResponse:
    """
    Send a message to a chat channel.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    
    **Request Body:**
    - **content**: Message content (required, 1-10000 characters)
    - **message_type**: Type of message (text, file, image, system, announcement)
    - **mentioned_users**: List of user IDs mentioned in the message
    - **attachments**: List of file attachments
    - **parent_message_id**: Parent message ID for replies
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Set channel_id from path
        message_data.channel_id = channel_id
        
        # Send message
        new_message = await chat_service.send_message(
            message_data=message_data,
            sender_id=current_user_id
        )
        
        # Add real-time WebSocket notification
        background_tasks.add_task(
            chat_websocket_manager.handle_new_message,
            channel_id=channel_id,
            message_data=ChatMessageResponse.from_orm(new_message).dict(),
            sender_id=current_user_id
        )
        
        logger.info(f"Message sent: {new_message.id} in channel {channel_id}")
        
        return ChatMessageResponse.from_orm(new_message)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

@router.get(
    "/channels/{channel_id}/messages",
    response_model=ChatMessagePaginatedResponse,
    summary="Get Channel Messages",
    description="Get messages from a chat channel with pagination and filtering",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_messages")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def get_channel_messages(
    channel_id: UUID = Path(..., description="Channel ID"),
    message_type: Optional[MessageType] = Query(None, description="Filter by message type"),
    sender_id: Optional[UUID] = Query(None, description="Filter by sender"),
    parent_message_id: Optional[UUID] = Query(None, description="Filter by parent message (thread)"),
    is_pinned: Optional[bool] = Query(None, description="Filter by pinned status"),
    search_query: Optional[str] = Query(None, description="Search in message content"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatMessagePaginatedResponse:
    """
    Get messages from a chat channel with pagination and filtering.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    
    **Query Parameters:**
    - **message_type**: Filter by message type
    - **sender_id**: Filter by message sender
    - **parent_message_id**: Filter by parent message (for threads)
    - **is_pinned**: Filter by pinned status
    - **search_query**: Search in message content
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 50, max: 100)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Create filter params
        filters = ChatMessageFilterParams(
            message_type=message_type,
            sender_id=sender_id,
            parent_message_id=parent_message_id,
            is_pinned=is_pinned,
            search_query=search_query
        )
        
        # Calculate offset
        offset = (page - 1) * size
        
        # Get messages
        messages, total = await chat_service.get_channel_messages(
            channel_id=channel_id,
            filters=filters,
            page=page,
            limit=size,
            offset=offset
        )
        
        # Calculate pagination info
        pages = (total + size - 1) // size
        
        return ChatMessagePaginatedResponse(
            items=[ChatMessageResponse.from_orm(message) for message in messages],
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Failed to get channel messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get channel messages"
        )

@router.put(
    "/messages/{message_id}",
    response_model=ChatMessageResponse,
    summary="Update Message",
    description="Update a chat message",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.update_message")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def update_message(
    message_id: UUID = Path(..., description="Message ID"),
    message_data: ChatMessageUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChatMessageResponse:
    """
    Update a chat message.
    
    **Path Parameters:**
    - **message_id**: Unique identifier of the message
    
    **Request Body:**
    - **content**: New message content (optional)
    - **is_pinned**: Pin/unpin message (optional, requires moderator/admin rights)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Update message
        updated_message = await chat_service.update_message(
            message_id=message_id,
            message_data=message_data,
            updated_by=current_user_id
        )
        
        if not updated_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Add real-time WebSocket notification
        background_tasks.add_task(
            chat_websocket_manager.handle_message_update,
            channel_id=updated_message.channel_id,
            message_data=ChatMessageResponse.from_orm(updated_message).dict(),
            updated_by=current_user_id
        )
        
        logger.info(f"Message updated: {message_id}")
        
        return ChatMessageResponse.from_orm(updated_message)
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update message {message_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update message"
        )

@router.delete(
    "/messages/{message_id}",
    response_model=Dict[str, Any],
    summary="Delete Message",
    description="Delete a chat message",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.delete_message")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def delete_message(
    message_id: UUID = Path(..., description="Message ID"),
    hard_delete: bool = Query(False, description="Permanently delete message"),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> Dict[str, Any]:
    """
    Delete a chat message.
    
    **Path Parameters:**
    - **message_id**: Unique identifier of the message
    
    **Query Parameters:**
    - **hard_delete**: If true, permanently delete; if false, soft delete (default: false)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Delete message
        success = await chat_service.delete_message(
            message_id=message_id,
            deleted_by=current_user_id,
            hard_delete=hard_delete
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Add real-time WebSocket notification
        # Note: We need the channel_id for this, would need to get it from the message
        # background_tasks.add_task(
        #     chat_websocket_manager.handle_message_deletion,
        #     channel_id=channel_id,  # Would need to fetch this
        #     message_id=message_id,
        #     deleted_by=current_user_id
        # )
        
        logger.info(f"Message {'permanently' if hard_delete else 'soft'} deleted: {message_id}")
        
        return {
            "message": f"Message {'permanently deleted' if hard_delete else 'removed'} successfully",
            "message_id": str(message_id),
            "hard_delete": hard_delete
        }
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete message {message_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete message"
        )

# ================================
# Message Reaction Endpoints
# ================================

@router.post(
    "/messages/{message_id}/reactions",
    response_model=MessageReactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Reaction",
    description="Add a reaction to a message",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.react_message")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def add_message_reaction(
    message_id: UUID = Path(..., description="Message ID"),
    reaction_data: MessageReactionCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> MessageReactionResponse:
    """
    Add a reaction to a message.
    
    **Path Parameters:**
    - **message_id**: Unique identifier of the message
    
    **Request Body:**
    - **emoji**: Emoji reaction (required, 1-50 characters)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Set message_id from path
        reaction_data.message_id = message_id
        
        # Add reaction
        new_reaction = await chat_service.add_reaction(
            reaction_data=reaction_data,
            employee_id=current_user_id
        )
        
        # Add real-time WebSocket notification
        # Note: We would need the channel_id from the message for this
        # background_tasks.add_task(
        #     chat_websocket_manager.handle_reaction_added,
        #     channel_id=channel_id,  # Would need to fetch this from message
        #     message_id=message_id,
        #     reaction_data=MessageReactionResponse.from_orm(new_reaction).dict(),
        #     user_id=current_user_id
        # )
        
        logger.info(f"Reaction added: {new_reaction.id} to message {message_id}")
        
        return MessageReactionResponse.from_orm(new_reaction)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to add reaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add reaction"
        )

@router.delete(
    "/messages/{message_id}/reactions/{emoji}",
    response_model=Dict[str, Any],
    summary="Remove Reaction",
    description="Remove a reaction from a message",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.react_message")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def remove_message_reaction(
    message_id: UUID = Path(..., description="Message ID"),
    emoji: str = Path(..., description="Emoji to remove"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> Dict[str, Any]:
    """
    Remove a reaction from a message.
    
    **Path Parameters:**
    - **message_id**: Unique identifier of the message
    - **emoji**: Emoji reaction to remove
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Remove reaction
        success = await chat_service.remove_reaction(
            message_id=message_id,
            employee_id=current_user_id,
            emoji=emoji
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reaction not found"
            )
        
        logger.info(f"Reaction {emoji} removed from message {message_id}")
        
        return {
            "message": "Reaction removed successfully",
            "message_id": str(message_id),
            "emoji": emoji
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove reaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove reaction"
        )

# ================================
# Direct Message Endpoints
# ================================

@router.post(
    "/direct-messages",
    response_model=DirectMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Direct Message",
    description="Send a direct message to another user",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.send_direct_message")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def send_direct_message(
    message_data: DirectMessageCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> DirectMessageResponse:
    """
    Send a direct message to another user.
    
    **Request Body:**
    - **recipient_id**: ID of the message recipient (required)
    - **content**: Message content (required, 1-10000 characters)
    - **message_type**: Type of message (text, file, image)
    - **attachments**: List of file attachments
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Send direct message
        new_message = await chat_service.send_direct_message(
            message_data=message_data,
            sender_id=current_user_id
        )
        
        # Add real-time WebSocket notification
        background_tasks.add_task(
            chat_websocket_manager.handle_direct_message,
            recipient_id=message_data.recipient_id,
            message_data=DirectMessageResponse.from_orm(new_message).dict(),
            sender_id=current_user_id
        )
        
        logger.info(f"Direct message sent: {new_message.id}")
        
        return DirectMessageResponse.from_orm(new_message)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to send direct message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send direct message"
        )

@router.get(
    "/direct-messages/{user_id}",
    response_model=DirectMessagePaginatedResponse,
    summary="Get Direct Messages",
    description="Get direct messages between current user and another user",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_direct_messages")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def get_direct_messages(
    user_id: UUID = Path(..., description="Other user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> DirectMessagePaginatedResponse:
    """
    Get direct messages between current user and another user.
    
    **Path Parameters:**
    - **user_id**: ID of the other user in the conversation
    
    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 50, max: 100)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Get direct messages
        messages, total = await chat_service.get_direct_messages(
            user1_id=current_user_id,
            user2_id=user_id,
            page=page,
            size=size
        )
        
        # Calculate pagination info
        pages = (total + size - 1) // size
        
        return DirectMessagePaginatedResponse(
            items=[DirectMessageResponse.from_orm(message) for message in messages],
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Failed to get direct messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get direct messages"
        )

@router.put(
    "/direct-messages/{user_id}/mark-read",
    response_model=Dict[str, Any],
    summary="Mark Direct Messages as Read",
    description="Mark all direct messages from a user as read",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_direct_messages")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def mark_direct_messages_read(
    user_id: UUID = Path(..., description="Sender user ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> Dict[str, Any]:
    """
    Mark all direct messages from a user as read.
    
    **Path Parameters:**
    - **user_id**: ID of the user whose messages to mark as read
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Mark messages as read
        messages_updated = await chat_service.mark_direct_messages_as_read(
            sender_id=user_id,
            recipient_id=current_user_id
        )
        
        logger.info(f"Marked {messages_updated} direct messages as read")
        
        return {
            "message": f"Marked {messages_updated} messages as read",
            "sender_id": str(user_id),
            "messages_updated": messages_updated
        }
        
    except Exception as e:
        logger.error(f"Failed to mark messages as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark messages as read"
        )

# ================================
# Online Status Endpoints
# ================================

@router.put(
    "/online-status",
    response_model=OnlineStatusResponse,
    summary="Update Online Status",
    description="Update current user's online status",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.update_status")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE]))
    ]
)
async def update_online_status(
    status_data: OnlineStatusUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> OnlineStatusResponse:
    """
    Update current user's online status.
    
    **Request Body:**
    - **status**: Online status (online, away, busy, offline)
    - **custom_status**: Custom status message (optional, max 255 characters)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Update online status
        updated_status = await chat_service.update_online_status(
            employee_id=current_user_id,
            status_data=status_data
        )
        
        # Add real-time WebSocket notification
        background_tasks.add_task(
            chat_websocket_manager.handle_online_status_change,
            user_id=current_user_id,
            status_data=OnlineStatusResponse.from_orm(updated_status).dict()
        )
        
        logger.info(f"Online status updated for user {current_user_id}: {status_data.status.value}")
        
        return OnlineStatusResponse.from_orm(updated_status)
        
    except Exception as e:
        logger.error(f"Failed to update online status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update online status"
        )

@router.get(
    "/online-status/{user_id}",
    response_model=OnlineStatusResponse,
    summary="Get User Online Status",
    description="Get a user's current online status",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_status")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def get_user_online_status(
    user_id: UUID = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> OnlineStatusResponse:
    """
    Get a user's current online status.
    
    **Path Parameters:**
    - **user_id**: Unique identifier of the user
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Get online status
        status = await chat_service.get_user_online_status(user_id)
        
        if not status:
            # Return default offline status
            return OnlineStatusResponse(
                id=user_id,  # This is not accurate but needed for response
                employee_id=user_id,
                status=OnlineStatusEnum.OFFLINE,
                custom_status=None,
                last_seen=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=None
            )
        
        return OnlineStatusResponse.from_orm(status)
        
    except Exception as e:
        logger.error(f"Failed to get user online status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user online status"
        )

@router.get(
    "/online-users",
    response_model=List[OnlineStatusResponse],
    summary="Get Online Users",
    description="Get list of currently online users",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_status")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def get_online_users(
    exclude_offline: bool = Query(True, description="Exclude offline users"),
    last_seen_minutes: int = Query(5, ge=1, le=60, description="Minutes since last seen"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> List[OnlineStatusResponse]:
    """
    Get list of currently online users.
    
    **Query Parameters:**
    - **exclude_offline**: Exclude offline users (default: true)
    - **last_seen_minutes**: Maximum minutes since last seen (default: 5, max: 60)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Get online users
        online_users = await chat_service.get_online_users(
            exclude_offline=exclude_offline,
            last_seen_minutes=last_seen_minutes
        )
        
        return [OnlineStatusResponse.from_orm(status) for status in online_users]
        
    except Exception as e:
        logger.error(f"Failed to get online users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get online users"
        )

# ================================
# Search and Analytics Endpoints
# ================================

@router.post(
    "/search/messages",
    response_model=MessageSearchResponse,
    summary="Search Messages",
    description="Search messages across accessible channels",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.search_messages")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def search_messages(
    search_request: MessageSearchRequest = Body(...),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> MessageSearchResponse:
    """
    Search messages across accessible channels.
    
    **Request Body:**
    - **query**: Search query (required, 1-500 characters)
    - **channel_ids**: Specific channels to search (optional)
    - **sender_ids**: Specific senders to filter (optional)
    - **message_types**: Message types to filter (optional)
    - **date_from**: Start date filter (optional)
    - **date_to**: End date filter (optional)
    - **include_archived**: Include archived channels (default: false)
    
    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Search messages
        messages, total = await chat_service.search_messages(
            search_request=search_request,
            user_id=current_user_id,
            page=page,
            size=size
        )
        
        return MessageSearchResponse(
            messages=[ChatMessageResponse.from_orm(message) for message in messages],
            total=total,
            query=search_request.query,
            highlights=[]  # Could implement text highlighting here
        )
        
    except Exception as e:
        logger.error(f"Failed to search messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search messages"
        )

@router.get(
    "/channels/{channel_id}/statistics",
    response_model=ChannelStatistics,
    summary="Get Channel Statistics",
    description="Get statistics for a specific channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_analytics")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD]))
    ]
)
async def get_channel_statistics(
    channel_id: UUID = Path(..., description="Channel ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> ChannelStatistics:
    """
    Get statistics for a specific channel.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    """
    try:
        chat_service = EnhancedChatService(db)
        
        # Get channel statistics
        stats = await chat_service.get_channel_statistics(channel_id)
        
        return ChannelStatistics(
            total_messages=stats.get("total_messages", 0),
            total_members=stats.get("total_members", 0),
            active_members_today=0,  # Would implement this
            messages_today=stats.get("messages_today", 0),
            most_active_member=None  # Would implement this
        )
        
    except Exception as e:
        logger.error(f"Failed to get channel statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get channel statistics"
        )

# ================================
# Bulk Operations
# ================================

@router.post(
    "/channels/{channel_id}/members/bulk-add",
    response_model=BulkOperationResponse,
    summary="Bulk Add Members",
    description="Add multiple members to a channel at once",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.manage_members")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD]))
    ]
)
async def bulk_add_members(
    channel_id: UUID = Path(..., description="Channel ID"),
    bulk_request: BulkMemberAddRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = Depends(),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> BulkOperationResponse:
    """
    Add multiple members to a channel at once.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    
    **Request Body:**
    - **employee_ids**: List of employee IDs to add (max 100)
    - **role**: Role to assign to all members
    """
    try:
        chat_service = EnhancedChatService(db)
        
        successful = []
        failed = []
        
        # Add members one by one (could be optimized with bulk operations)
        for employee_id in bulk_request.employee_ids:
            try:
                member_data = ChatMemberCreate(
                    channel_id=channel_id,
                    employee_id=employee_id,
                    role=bulk_request.role
                )
                
                await chat_service.add_member_to_channel(
                    member_data=member_data,
                    added_by=current_user_id
                )
                
                successful.append(employee_id)
                
            except Exception as e:
                failed.append({
                    "employee_id": str(employee_id),
                    "error": str(e)
                })
        
        logger.info(f"Bulk add completed: {len(successful)} successful, {len(failed)} failed")
        
        return BulkOperationResponse(
            successful=successful,
            failed=failed,
            total_processed=len(bulk_request.employee_ids),
            success_count=len(successful),
            failure_count=len(failed)
        )
        
    except Exception as e:
        logger.error(f"Failed to bulk add members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk add members"
        )

# ================================
# WebSocket Connection
# ================================

@router.websocket("/ws/{channel_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel_id: UUID,
    # TODO: Implement WebSocket authentication
    # For now, user_id would come from token validation
    user_id: Optional[UUID] = Query(None, description="User ID for authentication")
):
    """
    WebSocket endpoint for real-time chat communication.
    
    **Path Parameters:**
    - **channel_id**: Channel to connect to
    
    **Query Parameters:**
    - **user_id**: User ID for authentication (temporary - should use token)
    
    **WebSocket Messages:**
    - **message**: Send a new message
    - **typing_start**: Indicate user started typing
    - **typing_stop**: Indicate user stopped typing
    """
    if not user_id:
        await websocket.close(code=4001, reason="Authentication required")
        return
        
    try:
        # Connect user to channel
        await chat_websocket_manager.connect(websocket, channel_id, user_id)
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                # Handle different message types
                message_type = data.get("type")
                
                if message_type == "message":
                    await handle_websocket_message(websocket, channel_id, user_id, data)
                elif message_type == "typing_start":
                    await handle_typing_indicator(websocket, channel_id, user_id, True)
                elif message_type == "typing_stop":
                    await handle_typing_indicator(websocket, channel_id, user_id, False)
                elif message_type == "ping":
                    # Handle ping for connection keep-alive
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to process message",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for channel {channel_id}, user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up connection
        await chat_websocket_manager.disconnect(channel_id, user_id)

async def handle_websocket_message(websocket: WebSocket, channel_id: UUID, user_id: UUID, data: dict):
    """Handle WebSocket message sending"""
    try:
        # Extract message content
        content = data.get("content", "").strip()
        if not content:
            await websocket.send_json({
                "type": "error",
                "message": "Message content is required",
                "timestamp": datetime.utcnow().isoformat()
            })
            return
            
        # Create message data (simplified for WebSocket)
        message_data = {
            "channel_id": str(channel_id),
            "content": content,
            "message_type": data.get("message_type", "text"),
            "sender_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to channel (excluding sender)
        await chat_websocket_manager.handle_new_message(
            channel_id=channel_id,
            message_data=message_data,
            sender_id=user_id
        )
        
        # Send confirmation to sender
        await websocket.send_json({
            "type": "message_sent",
            "message": message_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"WebSocket message sent in channel {channel_id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to handle WebSocket message: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": "Failed to send message",
            "timestamp": datetime.utcnow().isoformat()
        })

async def handle_typing_indicator(websocket: WebSocket, channel_id: UUID, user_id: UUID, is_typing: bool):
    """Handle typing indicator"""
    try:
        # Broadcast typing indicator
        await chat_websocket_manager.handle_typing_indicator(
            channel_id=channel_id,
            user_id=user_id,
            is_typing=is_typing
        )
        
        logger.debug(f"Typing indicator: User {user_id} {'started' if is_typing else 'stopped'} typing in channel {channel_id}")
        
    except Exception as e:
        logger.error(f"Failed to handle typing indicator: {str(e)}")

# ================================
# WebSocket Utility Endpoints
# ================================

@router.get(
    "/channels/{channel_id}/online-users",
    response_model=List[Dict[str, Any]],
    summary="Get Online Users in Channel",
    description="Get list of users currently connected to a channel via WebSocket",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def get_channel_online_users(
    channel_id: UUID = Path(..., description="Channel ID"),
    current_user_id: UUID = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id)
) -> List[Dict[str, Any]]:
    """
    Get list of users currently connected to a channel via WebSocket.
    
    **Path Parameters:**
    - **channel_id**: Unique identifier of the channel
    """
    try:
        # Get connected users
        connected_users = await chat_websocket_manager.get_channel_users(channel_id)
        
        # Get typing users
        typing_users = await chat_websocket_manager.get_typing_users(channel_id)
        
        # Build response
        online_users = []
        for user_id_str in connected_users:
            online_users.append({
                "user_id": user_id_str,
                "is_typing": user_id_str in typing_users,
                "connected_at": datetime.utcnow().isoformat()  # This could be tracked more accurately
            })
            
        return online_users
        
    except Exception as e:
        logger.error(f"Failed to get channel online users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get channel online users"
        )

