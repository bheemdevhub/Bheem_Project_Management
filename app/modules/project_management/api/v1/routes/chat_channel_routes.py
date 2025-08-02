"""
FastAPI routes for ChatChannel API
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.modules.auth.core.services.permissions_service import (
    require_roles, require_api_permission, get_current_user_id, get_current_company_id
)
from app.shared.models import UserRole
from app.modules.project_management.core.services.chat_channel_service import ChatChannelService
from app.modules.project_management.core.schemas.chat_channel_schemas import (
    ChatChannelCreate, ChatChannelUpdate, ChatChannelResponse, ChatChannelDetailResponse,
    ChatChannelPaginatedResponse, ChatChannelFilterParams
)

router = APIRouter(
    prefix="/channels",
    tags=["Project Management - Chat Channels"],
    responses={404: {"description": "Not found"}}
)

@router.post(
    "",
    response_model=ChatChannelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Chat Channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.create_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD]))
    ]
)
async def create_chat_channel(
    channel_data: ChatChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
) -> ChatChannelResponse:
    service = ChatChannelService(db)
    channel = await service.create_channel(channel_data, created_by=current_user_id)
    return ChatChannelResponse.from_orm(channel)

@router.get(
    "",
    response_model=ChatChannelPaginatedResponse,
    summary="List Chat Channels",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def list_chat_channels(
    channel_type: Optional[str] = Query(None),
    project_id: Optional[UUID] = Query(None),
    is_private: Optional[bool] = Query(None),
    is_archived: Optional[bool] = Query(None),
    name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> ChatChannelPaginatedResponse:
    service = ChatChannelService(db)
    filters = ChatChannelFilterParams(
        channel_type=channel_type,
        project_id=project_id,
        is_private=is_private,
        is_archived=is_archived,
        name=name
    )
    items, total = await service.list_channels(filters, page, size)
    pages = (total + size - 1) // size
    return ChatChannelPaginatedResponse(
        items=[ChatChannelResponse.from_orm(c) for c in items],
        total=total, page=page, size=size, pages=pages
    )

@router.get(
    "/{channel_id}",
    response_model=ChatChannelDetailResponse,
    summary="Get Chat Channel Details",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.read_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD, UserRole.EMPLOYEE, UserRole.VIEWER]))
    ]
)
async def get_chat_channel(
    channel_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db)
) -> ChatChannelDetailResponse:
    service = ChatChannelService(db)
    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChatChannelDetailResponse.from_orm(channel)

@router.put(
    "/{channel_id}",
    response_model=ChatChannelResponse,
    summary="Update Chat Channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.update_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_LEAD]))
    ]
)
async def update_chat_channel(
    channel_id: UUID = Path(...),
    channel_data: ChatChannelUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
) -> ChatChannelResponse:
    service = ChatChannelService(db)
    channel = await service.update_channel(channel_id, channel_data, updated_by=current_user_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChatChannelResponse.from_orm(channel)

@router.delete(
    "/{channel_id}",
    response_model=Dict[str, Any],
    summary="Delete or Archive Chat Channel",
    dependencies=[
        Depends(lambda: require_api_permission("pm.chat.delete_channel")),
        Depends(require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER]))
    ]
)
async def delete_chat_channel(
    channel_id: UUID = Path(...),
    hard_delete: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
) -> Dict[str, Any]:
    service = ChatChannelService(db)
    success = await service.delete_channel(channel_id, deleted_by=current_user_id, hard_delete=hard_delete)
    if not success:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"message": "Channel deleted" if hard_delete else "Channel archived", "channel_id": str(channel_id)}
