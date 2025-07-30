# app/modules/project_management/core/services/enhanced_chat_service.py
"""
Enhanced Chat and Collaboration Service for Project Management Module
Comprehensive business logic for chat channels, messages, reactions, and online status
"""
import asyncio
from typing import List, Optional, Dict, Any, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime, timedelta
from uuid import UUID
import logging
import json

from bheem_core.modules.project_management.core.models.project_models import (
    ChatChannel, ChatMember, ChatMessage, MessageReaction, 
    DirectMessage, OnlineStatus
)
from bheem_core.modules.project_management.core.schemas.enhanced_chat_schemas import (
    # Channel schemas
    ChatChannelCreate, ChatChannelUpdate, ChatChannelFilterParams,
    # Member schemas
    ChatMemberCreate, ChatMemberUpdate, BulkMemberAddRequest, BulkMemberRemoveRequest,
    # Message schemas
    ChatMessageCreate, ChatMessageUpdate, ChatMessageFilterParams,
    # Reaction schemas
    MessageReactionCreate,
    # Direct message schemas
    DirectMessageCreate,
    # Online status schemas
    OnlineStatusUpdate,
    # Enum imports
    ChannelType, MemberRole, MessageType, OnlineStatusEnum, MessageStatus,
    # Search schemas
    MessageSearchRequest
)
from bheem_core.modules.project_management.events.enhanced_chat_events import (
    ChatEventDispatcher, ChannelCreatedEvent, ChannelUpdatedEvent, ChannelDeletedEvent,
    MemberJoinedEvent, MemberLeftEvent, MemberRoleChangedEvent,
    MessageSentEvent, MessageUpdatedEvent, MessageDeletedEvent,
    ReactionAddedEvent, ReactionRemovedEvent,
    DirectMessageSentEvent, OnlineStatusChangedEvent
)

logger = logging.getLogger(__name__)

class EnhancedChatService:
    """Enhanced service for handling chat and collaboration operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_dispatcher = ChatEventDispatcher()
    
    # ================================
    # Chat Channel Operations
    # ================================
    
    async def create_channel(
        self, 
        channel_data: ChatChannelCreate, 
        created_by: UUID
    ) -> ChatChannel:
        """Create a new chat channel"""
        try:
            # Check if channel name exists in same project/type scope
            existing_channel = await self._check_channel_name_exists(
                channel_data.name, 
                channel_data.project_id, 
                channel_data.channel_type
            )
            
            if existing_channel:
                raise ValueError(f"Channel '{channel_data.name}' already exists in this scope")
            
            # Create channel
            new_channel = ChatChannel(
                name=channel_data.name,
                description=channel_data.description,
                channel_type=channel_data.channel_type.value,
                is_private=channel_data.is_private,
                project_id=channel_data.project_id,
                created_by=created_by
            )
            
            self.db.add(new_channel)
            await self.db.flush()
            
            # Add creator as admin member
            creator_member = ChatMember(
                channel_id=new_channel.id,
                employee_id=created_by,
                role=MemberRole.ADMIN.value,
                joined_at=datetime.utcnow()
            )
            
            self.db.add(creator_member)
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(ChannelCreatedEvent(
                channel_id=new_channel.id,
                channel_name=new_channel.name,
                channel_type=new_channel.channel_type,
                created_by=created_by,
                project_id=new_channel.project_id,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Channel created: {new_channel.id} by user {created_by}")
            return new_channel
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create channel: {str(e)}")
            raise
    
    async def get_channel_by_id(
        self, 
        channel_id: UUID, 
        include_members: bool = False,
        include_recent_messages: bool = False
    ) -> Optional[ChatChannel]:
        """Get channel by ID with optional related data"""
        try:
            query = select(ChatChannel).where(
                and_(
                    ChatChannel.id == channel_id,
                    ChatChannel.is_active == True
                )
            )
            
            if include_members:
                query = query.options(selectinload(ChatChannel.members))
            
            result = await self.db.execute(query)
            channel = result.scalar_one_or_none()
            
            if channel and include_recent_messages:
                # Get recent messages separately to avoid complex joins
                recent_messages = await self.get_channel_messages(
                    channel_id=channel_id,
                    limit=10,
                    offset=0
                )
                # Note: You would set this as an attribute or return as tuple
                
            return channel
            
        except Exception as e:
            logger.error(f"Failed to get channel {channel_id}: {str(e)}")
            raise
    
    async def list_channels(
        self,
        filters: ChatChannelFilterParams,
        employee_id: Optional[UUID] = None,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_desc: bool = True
    ) -> Tuple[List[ChatChannel], int]:
        """List channels with filtering and pagination"""
        try:
            # Base query
            query = select(ChatChannel).where(ChatChannel.is_active == True)
            count_query = select(func.count(ChatChannel.id)).where(ChatChannel.is_active == True)
            
            # Apply filters
            if filters.channel_type:
                query = query.where(ChatChannel.channel_type == filters.channel_type.value)
                count_query = count_query.where(ChatChannel.channel_type == filters.channel_type.value)
            
            if filters.project_id:
                query = query.where(ChatChannel.project_id == filters.project_id)
                count_query = count_query.where(ChatChannel.project_id == filters.project_id)
            
            if filters.is_private is not None:
                query = query.where(ChatChannel.is_private == filters.is_private)
                count_query = count_query.where(ChatChannel.is_private == filters.is_private)
            
            if filters.is_archived is not None:
                query = query.where(ChatChannel.is_archived == filters.is_archived)
                count_query = count_query.where(ChatChannel.is_archived == filters.is_archived)
            
            # Filter by member access if employee_id provided
            if employee_id:
                member_subquery = select(ChatMember.channel_id).where(
                    and_(
                        ChatMember.employee_id == employee_id,
                        ChatMember.is_active == True
                    )
                )
                query = query.where(
                    or_(
                        ChatChannel.is_private == False,  # Public channels
                        ChatChannel.id.in_(member_subquery)  # Private channels user is member of
                    )
                )
                count_query = count_query.where(
                    or_(
                        ChatChannel.is_private == False,
                        ChatChannel.id.in_(member_subquery)
                    )
                )
            
            # Apply sorting
            if sort_by == "name":
                order_col = ChatChannel.name
            elif sort_by == "member_count":
                # Would need a subquery for member count
                order_col = ChatChannel.created_at
            else:
                order_col = getattr(ChatChannel, sort_by, ChatChannel.created_at)
            
            if sort_desc:
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(asc(order_col))
            
            # Apply pagination
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)
            
            # Execute queries
            result = await self.db.execute(query)
            channels = result.scalars().all()
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            return list(channels), total
            
        except Exception as e:
            logger.error(f"Failed to list channels: {str(e)}")
            raise
    
    async def update_channel(
        self,
        channel_id: UUID,
        channel_data: ChatChannelUpdate,
        updated_by: UUID
    ) -> Optional[ChatChannel]:
        """Update channel information"""
        try:
            # Get channel and verify permissions
            channel = await self.get_channel_by_id(channel_id)
            if not channel:
                return None
            
            # Verify user has admin/moderator access
            if not await self._user_can_manage_channel(channel_id, updated_by):
                raise PermissionError("User does not have permission to update this channel")
            
            # Update fields
            if channel_data.name is not None:
                # Check name uniqueness
                existing = await self._check_channel_name_exists(
                    channel_data.name, 
                    channel.project_id, 
                    ChannelType(channel.channel_type),
                    exclude_id=channel_id
                )
                if existing:
                    raise ValueError(f"Channel name '{channel_data.name}' already exists")
                channel.name = channel_data.name
            
            if channel_data.description is not None:
                channel.description = channel_data.description
            
            if channel_data.is_private is not None:
                channel.is_private = channel_data.is_private
            
            if channel_data.is_archived is not None:
                channel.is_archived = channel_data.is_archived
            
            channel.updated_at = datetime.utcnow()
            channel.updated_by = updated_by
            
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(ChannelUpdatedEvent(
                channel_id=channel.id,
                channel_name=channel.name,
                updated_by=updated_by,
                changes=channel_data.dict(exclude_unset=True),
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Channel updated: {channel_id} by user {updated_by}")
            return channel
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update channel {channel_id}: {str(e)}")
            raise
    
    async def delete_channel(
        self,
        channel_id: UUID,
        deleted_by: UUID,
        hard_delete: bool = False
    ) -> bool:
        """Delete or soft-delete a channel"""
        try:
            # Get channel and verify permissions
            channel = await self.get_channel_by_id(channel_id)
            if not channel:
                return False
            
            # Verify user has admin access
            if not await self._user_can_manage_channel(channel_id, deleted_by, require_admin=True):
                raise PermissionError("User does not have permission to delete this channel")
            
            if hard_delete:
                # Hard delete - remove from database
                await self.db.delete(channel)
            else:
                # Soft delete - mark as inactive
                channel.is_active = False
                channel.updated_at = datetime.utcnow()
                channel.updated_by = deleted_by
            
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(ChannelDeletedEvent(
                channel_id=channel.id,
                channel_name=channel.name,
                deleted_by=deleted_by,
                hard_delete=hard_delete,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Channel {'hard' if hard_delete else 'soft'} deleted: {channel_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete channel {channel_id}: {str(e)}")
            raise
    
    # ================================
    # Chat Member Operations
    # ================================
    
    async def add_member_to_channel(
        self,
        member_data: ChatMemberCreate,
        added_by: UUID
    ) -> ChatMember:
        """Add a member to a channel"""
        try:
            # Verify channel exists and user has permission
            if not await self._user_can_manage_channel(member_data.channel_id, added_by):
                raise PermissionError("User does not have permission to add members to this channel")
            
            # Check if member already exists
            existing_member = await self._get_channel_member(
                member_data.channel_id, 
                member_data.employee_id
            )
            
            if existing_member:
                if existing_member.is_active:
                    raise ValueError("User is already a member of this channel")
                else:
                    # Reactivate existing member
                    existing_member.is_active = True
                    existing_member.role = member_data.role.value
                    existing_member.joined_at = datetime.utcnow()
                    await self.db.commit()
                    return existing_member
            
            # Create new member
            new_member = ChatMember(
                channel_id=member_data.channel_id,
                employee_id=member_data.employee_id,
                role=member_data.role.value,
                joined_at=datetime.utcnow()
            )
            
            self.db.add(new_member)
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(MemberJoinedEvent(
                channel_id=member_data.channel_id,
                employee_id=member_data.employee_id,
                role=member_data.role.value,
                added_by=added_by,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Member {member_data.employee_id} added to channel {member_data.channel_id}")
            return new_member
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to add member to channel: {str(e)}")
            raise
    
    async def remove_member_from_channel(
        self,
        channel_id: UUID,
        employee_id: UUID,
        removed_by: UUID
    ) -> bool:
        """Remove a member from a channel"""
        try:
            # Verify permissions
            if not await self._user_can_manage_channel(channel_id, removed_by):
                if removed_by != employee_id:  # Users can remove themselves
                    raise PermissionError("User does not have permission to remove members")
            
            # Get member
            member = await self._get_channel_member(channel_id, employee_id)
            if not member or not member.is_active:
                return False
            
            # Don't allow removing the last admin
            if member.role == MemberRole.ADMIN.value:
                admin_count = await self._count_channel_admins(channel_id)
                if admin_count <= 1:
                    raise ValueError("Cannot remove the last admin from the channel")
            
            # Soft delete member
            member.is_active = False
            member.updated_at = datetime.utcnow()
            member.updated_by = removed_by
            
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(MemberLeftEvent(
                channel_id=channel_id,
                employee_id=employee_id,
                removed_by=removed_by,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Member {employee_id} removed from channel {channel_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to remove member from channel: {str(e)}")
            raise
    
    async def update_member_role(
        self,
        channel_id: UUID,
        employee_id: UUID,
        new_role: MemberRole,
        updated_by: UUID
    ) -> Optional[ChatMember]:
        """Update a member's role in a channel"""
        try:
            # Verify permissions
            if not await self._user_can_manage_channel(channel_id, updated_by, require_admin=True):
                raise PermissionError("Only admins can change member roles")
            
            # Get member
            member = await self._get_channel_member(channel_id, employee_id)
            if not member or not member.is_active:
                return None
            
            # Don't allow demoting the last admin
            if member.role == MemberRole.ADMIN.value and new_role != MemberRole.ADMIN:
                admin_count = await self._count_channel_admins(channel_id)
                if admin_count <= 1:
                    raise ValueError("Cannot demote the last admin from the channel")
            
            old_role = member.role
            member.role = new_role.value
            member.updated_at = datetime.utcnow()
            member.updated_by = updated_by
            
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(MemberRoleChangedEvent(
                channel_id=channel_id,
                employee_id=employee_id,
                old_role=old_role,
                new_role=new_role.value,
                updated_by=updated_by,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Member {employee_id} role changed from {old_role} to {new_role.value}")
            return member
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update member role: {str(e)}")
            raise
    
    async def get_channel_members(
        self,
        channel_id: UUID,
        role_filter: Optional[MemberRole] = None,
        active_only: bool = True
    ) -> List[ChatMember]:
        """Get members of a channel"""
        try:
            query = select(ChatMember).where(ChatMember.channel_id == channel_id)
            
            if active_only:
                query = query.where(ChatMember.is_active == True)
            
            if role_filter:
                query = query.where(ChatMember.role == role_filter.value)
            
            query = query.order_by(ChatMember.joined_at)
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Failed to get channel members: {str(e)}")
            raise
    
    # ================================
    # Chat Message Operations
    # ================================
    
    async def send_message(
        self,
        message_data: ChatMessageCreate,
        sender_id: UUID
    ) -> ChatMessage:
        """Send a message to a channel"""
        try:
            # Verify user is member of channel
            if not await self._user_is_channel_member(message_data.channel_id, sender_id):
                raise PermissionError("User is not a member of this channel")
            
            # Verify parent message exists if this is a reply
            if message_data.parent_message_id:
                parent_message = await self._get_message_by_id(message_data.parent_message_id)
                if not parent_message or parent_message.channel_id != message_data.channel_id:
                    raise ValueError("Invalid parent message")
            
            # Create message
            new_message = ChatMessage(
                content=message_data.content,
                message_type=message_data.message_type.value,
                channel_id=message_data.channel_id,
                sender_id=sender_id,
                parent_message_id=message_data.parent_message_id,
                mentioned_users=message_data.mentioned_users or [],
                attachments=message_data.attachments or []
            )
            
            self.db.add(new_message)
            await self.db.flush()
            
            # Update parent message thread count if this is a reply
            if message_data.parent_message_id:
                await self._increment_thread_count(message_data.parent_message_id)
            
            # Update channel last message timestamp
            await self._update_channel_last_message(message_data.channel_id)
            
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(MessageSentEvent(
                message_id=new_message.id,
                channel_id=message_data.channel_id,
                sender_id=sender_id,
                content=message_data.content,
                message_type=message_data.message_type.value,
                mentioned_users=message_data.mentioned_users or [],
                parent_message_id=message_data.parent_message_id,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Message sent: {new_message.id} in channel {message_data.channel_id}")
            return new_message
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to send message: {str(e)}")
            raise
    
    async def get_channel_messages(
        self,
        channel_id: UUID,
        filters: Optional[ChatMessageFilterParams] = None,
        page: int = 1,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ChatMessage], int]:
        """Get messages from a channel with pagination"""
        try:
            # Build query
            query = select(ChatMessage).where(
                and_(
                    ChatMessage.channel_id == channel_id,
                    ChatMessage.is_active == True
                )
            )
            count_query = select(func.count(ChatMessage.id)).where(
                and_(
                    ChatMessage.channel_id == channel_id,
                    ChatMessage.is_active == True
                )
            )
            
            # Apply filters if provided
            if filters:
                if filters.message_type:
                    query = query.where(ChatMessage.message_type == filters.message_type.value)
                    count_query = count_query.where(ChatMessage.message_type == filters.message_type.value)
                
                if filters.sender_id:
                    query = query.where(ChatMessage.sender_id == filters.sender_id)
                    count_query = count_query.where(ChatMessage.sender_id == filters.sender_id)
                
                if filters.parent_message_id:
                    query = query.where(ChatMessage.parent_message_id == filters.parent_message_id)
                    count_query = count_query.where(ChatMessage.parent_message_id == filters.parent_message_id)
                
                if filters.is_pinned is not None:
                    query = query.where(ChatMessage.is_pinned == filters.is_pinned)
                    count_query = count_query.where(ChatMessage.is_pinned == filters.is_pinned)
                
                if filters.date_from:
                    query = query.where(ChatMessage.created_at >= filters.date_from)
                    count_query = count_query.where(ChatMessage.created_at >= filters.date_from)
                
                if filters.date_to:
                    query = query.where(ChatMessage.created_at <= filters.date_to)
                    count_query = count_query.where(ChatMessage.created_at <= filters.date_to)
                
                if filters.search_query:
                    search_pattern = f"%{filters.search_query}%"
                    query = query.where(ChatMessage.content.ilike(search_pattern))
                    count_query = count_query.where(ChatMessage.content.ilike(search_pattern))
            
            # Order by created_at descending (newest first)
            query = query.order_by(desc(ChatMessage.created_at))
            
            # Apply pagination
            if limit > 0:
                query = query.offset(offset).limit(limit)
            
            # Execute queries
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            return list(messages), total
            
        except Exception as e:
            logger.error(f"Failed to get channel messages: {str(e)}")
            raise
    
    async def update_message(
        self,
        message_id: UUID,
        message_data: ChatMessageUpdate,
        updated_by: UUID
    ) -> Optional[ChatMessage]:
        """Update a message"""
        try:
            # Get message and verify ownership
            message = await self._get_message_by_id(message_id)
            if not message:
                return None
            
            if message.sender_id != updated_by:
                # Check if user has moderator/admin rights in channel
                if not await self._user_can_manage_channel(message.channel_id, updated_by):
                    raise PermissionError("User can only edit their own messages")
            
            # Update fields
            if message_data.content is not None:
                message.content = message_data.content
                message.is_edited = True
            
            if message_data.is_pinned is not None:
                # Only mods/admins can pin/unpin
                if not await self._user_can_manage_channel(message.channel_id, updated_by):
                    raise PermissionError("Only moderators and admins can pin messages")
                message.is_pinned = message_data.is_pinned
            
            message.updated_at = datetime.utcnow()
            message.updated_by = updated_by
            
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(MessageUpdatedEvent(
                message_id=message.id,
                channel_id=message.channel_id,
                updated_by=updated_by,
                changes=message_data.dict(exclude_unset=True),
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Message updated: {message_id}")
            return message
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update message {message_id}: {str(e)}")
            raise
    
    async def delete_message(
        self,
        message_id: UUID,
        deleted_by: UUID,
        hard_delete: bool = False
    ) -> bool:
        """Delete a message"""
        try:
            # Get message and verify permissions
            message = await self._get_message_by_id(message_id)
            if not message:
                return False
            
            if message.sender_id != deleted_by:
                # Check if user has moderator/admin rights
                if not await self._user_can_manage_channel(message.channel_id, deleted_by):
                    raise PermissionError("User can only delete their own messages")
            
            if hard_delete:
                await self.db.delete(message)
            else:
                message.is_active = False
                message.updated_at = datetime.utcnow()
                message.updated_by = deleted_by
            
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(MessageDeletedEvent(
                message_id=message.id,
                channel_id=message.channel_id,
                deleted_by=deleted_by,
                hard_delete=hard_delete,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Message {'hard' if hard_delete else 'soft'} deleted: {message_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete message {message_id}: {str(e)}")
            raise
    
    # ================================
    # Message Reaction Operations
    # ================================
    
    async def add_reaction(
        self,
        reaction_data: MessageReactionCreate,
        employee_id: UUID
    ) -> MessageReaction:
        """Add a reaction to a message"""
        try:
            # Verify message exists and user has access
            message = await self._get_message_by_id(reaction_data.message_id)
            if not message:
                raise ValueError("Message not found")
            
            if not await self._user_is_channel_member(message.channel_id, employee_id):
                raise PermissionError("User is not a member of this channel")
            
            # Check if reaction already exists
            existing_reaction = await self._get_user_reaction(
                reaction_data.message_id, 
                employee_id, 
                reaction_data.emoji
            )
            
            if existing_reaction:
                if existing_reaction.is_active:
                    raise ValueError("User has already reacted with this emoji")
                else:
                    # Reactivate existing reaction
                    existing_reaction.is_active = True
                    existing_reaction.updated_at = datetime.utcnow()
                    await self.db.commit()
                    return existing_reaction
            
            # Create new reaction
            new_reaction = MessageReaction(
                message_id=reaction_data.message_id,
                employee_id=employee_id,
                emoji=reaction_data.emoji
            )
            
            self.db.add(new_reaction)
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(ReactionAddedEvent(
                reaction_id=new_reaction.id,
                message_id=reaction_data.message_id,
                employee_id=employee_id,
                emoji=reaction_data.emoji,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Reaction added: {new_reaction.id}")
            return new_reaction
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to add reaction: {str(e)}")
            raise
    
    async def remove_reaction(
        self,
        message_id: UUID,
        employee_id: UUID,
        emoji: str
    ) -> bool:
        """Remove a reaction from a message"""
        try:
            # Get reaction
            reaction = await self._get_user_reaction(message_id, employee_id, emoji)
            if not reaction or not reaction.is_active:
                return False
            
            # Soft delete reaction
            reaction.is_active = False
            reaction.updated_at = datetime.utcnow()
            reaction.updated_by = employee_id
            
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(ReactionRemovedEvent(
                reaction_id=reaction.id,
                message_id=message_id,
                employee_id=employee_id,
                emoji=emoji,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Reaction removed: {reaction.id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to remove reaction: {str(e)}")
            raise
    
    # ================================
    # Direct Message Operations
    # ================================
    
    async def send_direct_message(
        self,
        message_data: DirectMessageCreate,
        sender_id: UUID
    ) -> DirectMessage:
        """Send a direct message"""
        try:
            if sender_id == message_data.recipient_id:
                raise ValueError("Cannot send message to yourself")
            
            # Create direct message
            new_message = DirectMessage(
                content=message_data.content,
                message_type=message_data.message_type.value,
                sender_id=sender_id,
                recipient_id=message_data.recipient_id,
                attachments=message_data.attachments or []
            )
            
            self.db.add(new_message)
            await self.db.commit()
            
            # Dispatch event
            await self.event_dispatcher.dispatch(DirectMessageSentEvent(
                message_id=new_message.id,
                sender_id=sender_id,
                recipient_id=message_data.recipient_id,
                content=message_data.content,
                timestamp=datetime.utcnow()
            ))
            
            logger.info(f"Direct message sent: {new_message.id}")
            return new_message
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to send direct message: {str(e)}")
            raise
    
    async def get_direct_messages(
        self,
        user1_id: UUID,
        user2_id: UUID,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[DirectMessage], int]:
        """Get direct messages between two users"""
        try:
            # Build query for messages between the two users
            query = select(DirectMessage).where(
                and_(
                    DirectMessage.is_active == True,
                    or_(
                        and_(
                            DirectMessage.sender_id == user1_id,
                            DirectMessage.recipient_id == user2_id
                        ),
                        and_(
                            DirectMessage.sender_id == user2_id,
                            DirectMessage.recipient_id == user1_id
                        )
                    )
                )
            ).order_by(desc(DirectMessage.created_at))
            
            # Count query
            count_query = select(func.count(DirectMessage.id)).where(
                and_(
                    DirectMessage.is_active == True,
                    or_(
                        and_(
                            DirectMessage.sender_id == user1_id,
                            DirectMessage.recipient_id == user2_id
                        ),
                        and_(
                            DirectMessage.sender_id == user2_id,
                            DirectMessage.recipient_id == user1_id
                        )
                    )
                )
            )
            
            # Apply pagination
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)
            
            # Execute queries
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            return list(messages), total
            
        except Exception as e:
            logger.error(f"Failed to get direct messages: {str(e)}")
            raise
    
    async def mark_direct_messages_as_read(
        self,
        sender_id: UUID,
        recipient_id: UUID
    ) -> int:
        """Mark all unread direct messages from sender as read"""
        try:
            stmt = update(DirectMessage).where(
                and_(
                    DirectMessage.sender_id == sender_id,
                    DirectMessage.recipient_id == recipient_id,
                    DirectMessage.is_read == False,
                    DirectMessage.is_active == True
                )
            ).values(
                is_read=True,
                read_at=datetime.utcnow()
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            messages_updated = result.rowcount
            logger.info(f"Marked {messages_updated} messages as read")
            return messages_updated
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to mark messages as read: {str(e)}")
            raise
    
    # ================================
    # Online Status Operations
    # ================================
    
    async def update_online_status(
        self,
        employee_id: UUID,
        status_data: OnlineStatusUpdate
    ) -> OnlineStatus:
        """Update user's online status"""
        try:
            # Get or create online status record
            existing_status = await self._get_user_online_status(employee_id)
            
            if existing_status:
                # Update existing record
                old_status = existing_status.status
                existing_status.status = status_data.status.value
                existing_status.custom_status = status_data.custom_status
                existing_status.last_seen = datetime.utcnow()
                existing_status.updated_at = datetime.utcnow()
                
                await self.db.commit()
                
                # Dispatch event if status changed
                if old_status != status_data.status.value:
                    await self.event_dispatcher.dispatch(OnlineStatusChangedEvent(
                        employee_id=employee_id,
                        old_status=old_status,
                        new_status=status_data.status.value,
                        custom_status=status_data.custom_status,
                        timestamp=datetime.utcnow()
                    ))
                
                return existing_status
            else:
                # Create new record
                new_status = OnlineStatus(
                    employee_id=employee_id,
                    status=status_data.status.value,
                    custom_status=status_data.custom_status,
                    last_seen=datetime.utcnow()
                )
                
                self.db.add(new_status)
                await self.db.commit()
                
                # Dispatch event
                await self.event_dispatcher.dispatch(OnlineStatusChangedEvent(
                    employee_id=employee_id,
                    old_status=OnlineStatusEnum.OFFLINE.value,
                    new_status=status_data.status.value,
                    custom_status=status_data.custom_status,
                    timestamp=datetime.utcnow()
                ))
                
                return new_status
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update online status: {str(e)}")
            raise
    
    async def get_user_online_status(self, employee_id: UUID) -> Optional[OnlineStatus]:
        """Get user's current online status"""
        return await self._get_user_online_status(employee_id)
    
    async def get_online_users(
        self,
        exclude_offline: bool = True,
        last_seen_minutes: int = 5
    ) -> List[OnlineStatus]:
        """Get list of online users"""
        try:
            query = select(OnlineStatus).where(OnlineStatus.is_active == True)
            
            if exclude_offline:
                query = query.where(OnlineStatus.status != OnlineStatusEnum.OFFLINE.value)
            
            # Filter by last seen time
            cutoff_time = datetime.utcnow() - timedelta(minutes=last_seen_minutes)
            query = query.where(OnlineStatus.last_seen >= cutoff_time)
            
            query = query.order_by(desc(OnlineStatus.last_seen))
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Failed to get online users: {str(e)}")
            raise
    
    # ================================
    # Search Operations
    # ================================
    
    async def search_messages(
        self,
        search_request: MessageSearchRequest,
        user_id: UUID,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[ChatMessage], int]:
        """Search messages across channels"""
        try:
            # Base query
            query = select(ChatMessage).where(
                and_(
                    ChatMessage.is_active == True,
                    ChatMessage.content.ilike(f"%{search_request.query}%")
                )
            )
            
            count_query = select(func.count(ChatMessage.id)).where(
                and_(
                    ChatMessage.is_active == True,
                    ChatMessage.content.ilike(f"%{search_request.query}%")
                )
            )
            
            # Filter by user's accessible channels
            accessible_channels = await self._get_user_accessible_channels(user_id)
            if accessible_channels:
                channel_ids = [ch.id for ch in accessible_channels]
                query = query.where(ChatMessage.channel_id.in_(channel_ids))
                count_query = count_query.where(ChatMessage.channel_id.in_(channel_ids))
            else:
                # No accessible channels, return empty result
                return [], 0
            
            # Apply additional filters
            if search_request.channel_ids:
                # Intersect with user's accessible channels
                filtered_ids = [ch_id for ch_id in search_request.channel_ids if ch_id in channel_ids]
                if filtered_ids:
                    query = query.where(ChatMessage.channel_id.in_(filtered_ids))
                    count_query = count_query.where(ChatMessage.channel_id.in_(filtered_ids))
                else:
                    return [], 0
            
            if search_request.sender_ids:
                query = query.where(ChatMessage.sender_id.in_(search_request.sender_ids))
                count_query = count_query.where(ChatMessage.sender_id.in_(search_request.sender_ids))
            
            if search_request.message_types:
                type_values = [mt.value for mt in search_request.message_types]
                query = query.where(ChatMessage.message_type.in_(type_values))
                count_query = count_query.where(ChatMessage.message_type.in_(type_values))
            
            if search_request.date_from:
                query = query.where(ChatMessage.created_at >= search_request.date_from)
                count_query = count_query.where(ChatMessage.created_at >= search_request.date_from)
            
            if search_request.date_to:
                query = query.where(ChatMessage.created_at <= search_request.date_to)
                count_query = count_query.where(ChatMessage.created_at <= search_request.date_to)
            
            # Order by relevance/recency
            query = query.order_by(desc(ChatMessage.created_at))
            
            # Apply pagination
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)
            
            # Execute queries
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            return list(messages), total
            
        except Exception as e:
            logger.error(f"Failed to search messages: {str(e)}")
            raise
    
    # ================================
    # Analytics and Statistics
    # ================================
    
    async def get_channel_statistics(self, channel_id: UUID) -> Dict[str, Any]:
        """Get statistics for a channel"""
        try:
            # Message count
            message_count_query = select(func.count(ChatMessage.id)).where(
                and_(
                    ChatMessage.channel_id == channel_id,
                    ChatMessage.is_active == True
                )
            )
            message_count_result = await self.db.execute(message_count_query)
            total_messages = message_count_result.scalar()
            
            # Member count
            member_count_query = select(func.count(ChatMember.id)).where(
                and_(
                    ChatMember.channel_id == channel_id,
                    ChatMember.is_active == True
                )
            )
            member_count_result = await self.db.execute(member_count_query)
            total_members = member_count_result.scalar()
            
            # Messages today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            messages_today_query = select(func.count(ChatMessage.id)).where(
                and_(
                    ChatMessage.channel_id == channel_id,
                    ChatMessage.is_active == True,
                    ChatMessage.created_at >= today_start
                )
            )
            messages_today_result = await self.db.execute(messages_today_query)
            messages_today = messages_today_result.scalar()
            
            # Most active member (by message count)
            most_active_query = select(
                ChatMessage.sender_id,
                func.count(ChatMessage.id).label('message_count')
            ).where(
                and_(
                    ChatMessage.channel_id == channel_id,
                    ChatMessage.is_active == True
                )
            ).group_by(ChatMessage.sender_id).order_by(desc('message_count')).limit(1)
            
            most_active_result = await self.db.execute(most_active_query)
            most_active_row = most_active_result.first()
            
            return {
                "total_messages": total_messages,
                "total_members": total_members,
                "messages_today": messages_today,
                "most_active_member_id": most_active_row.sender_id if most_active_row else None,
                "most_active_member_message_count": most_active_row.message_count if most_active_row else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get channel statistics: {str(e)}")
            raise
    
    # ================================
    # Helper Methods
    # ================================
    
    async def _check_channel_name_exists(
        self,
        name: str,
        project_id: Optional[UUID],
        channel_type: ChannelType,
        exclude_id: Optional[UUID] = None
    ) -> Optional[ChatChannel]:
        """Check if channel name already exists in scope"""
        query = select(ChatChannel).where(
            and_(
                ChatChannel.name == name,
                ChatChannel.channel_type == channel_type.value,
                ChatChannel.project_id == project_id,
                ChatChannel.is_active == True
            )
        )
        
        if exclude_id:
            query = query.where(ChatChannel.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _user_can_manage_channel(
        self,
        channel_id: UUID,
        user_id: UUID,
        require_admin: bool = False
    ) -> bool:
        """Check if user can manage (add/remove members, update) channel"""
        query = select(ChatMember).where(
            and_(
                ChatMember.channel_id == channel_id,
                ChatMember.employee_id == user_id,
                ChatMember.is_active == True
            )
        )
        
        if require_admin:
            query = query.where(ChatMember.role == MemberRole.ADMIN.value)
        else:
            query = query.where(
                ChatMember.role.in_([MemberRole.ADMIN.value, MemberRole.MODERATOR.value])
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def _user_is_channel_member(
        self,
        channel_id: UUID,
        user_id: UUID
    ) -> bool:
        """Check if user is a member of the channel"""
        query = select(ChatMember).where(
            and_(
                ChatMember.channel_id == channel_id,
                ChatMember.employee_id == user_id,
                ChatMember.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def _get_channel_member(
        self,
        channel_id: UUID,
        employee_id: UUID
    ) -> Optional[ChatMember]:
        """Get channel member record"""
        query = select(ChatMember).where(
            and_(
                ChatMember.channel_id == channel_id,
                ChatMember.employee_id == employee_id
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _count_channel_admins(self, channel_id: UUID) -> int:
        """Count active admins in a channel"""
        query = select(func.count(ChatMember.id)).where(
            and_(
                ChatMember.channel_id == channel_id,
                ChatMember.role == MemberRole.ADMIN.value,
                ChatMember.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def _get_message_by_id(self, message_id: UUID) -> Optional[ChatMessage]:
        """Get message by ID"""
        query = select(ChatMessage).where(
            and_(
                ChatMessage.id == message_id,
                ChatMessage.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _increment_thread_count(self, parent_message_id: UUID) -> None:
        """Increment thread count for a parent message"""
        stmt = update(ChatMessage).where(
            ChatMessage.id == parent_message_id
        ).values(
            thread_count=ChatMessage.thread_count + 1
        )
        
        await self.db.execute(stmt)
    
    async def _update_channel_last_message(self, channel_id: UUID) -> None:
        """Update channel's last message timestamp"""
        stmt = update(ChatChannel).where(
            ChatChannel.id == channel_id
        ).values(
            last_message_at=datetime.utcnow()
        )
        
        await self.db.execute(stmt)
    
    async def _get_user_reaction(
        self,
        message_id: UUID,
        employee_id: UUID,
        emoji: str
    ) -> Optional[MessageReaction]:
        """Get user's reaction to a message"""
        query = select(MessageReaction).where(
            and_(
                MessageReaction.message_id == message_id,
                MessageReaction.employee_id == employee_id,
                MessageReaction.emoji == emoji
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_user_online_status(self, employee_id: UUID) -> Optional[OnlineStatus]:
        """Get user's online status record"""
        query = select(OnlineStatus).where(
            and_(
                OnlineStatus.employee_id == employee_id,
                OnlineStatus.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_user_accessible_channels(self, user_id: UUID) -> List[ChatChannel]:
        """Get channels that user has access to"""
        # Get channels where user is a member
        member_channels_query = select(ChatChannel).join(ChatMember).where(
            and_(
                ChatMember.employee_id == user_id,
                ChatMember.is_active == True,
                ChatChannel.is_active == True
            )
        )
        
        # Get public channels
        public_channels_query = select(ChatChannel).where(
            and_(
                ChatChannel.is_private == False,
                ChatChannel.is_active == True
            )
        )
        
        # Union the queries
        member_result = await self.db.execute(member_channels_query)
        member_channels = member_result.scalars().all()
        
        public_result = await self.db.execute(public_channels_query)
        public_channels = public_result.scalars().all()
        
        # Combine and deduplicate
        all_channels = list(member_channels) + list(public_channels)
        seen_ids = set()
        unique_channels = []
        
        for channel in all_channels:
            if channel.id not in seen_ids:
                unique_channels.append(channel)
                seen_ids.add(channel.id)
        
        return unique_channels

