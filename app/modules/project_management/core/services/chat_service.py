# app/modules/project_management/core/services/chat_service.py
"""
Chat and Collaboration Service for Project Management Module
Handles all business logic for chat channels, messages, and online status
"""
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime, timedelta
from uuid import UUID
import logging

from app.modules.project_management.core.models.project_models import (
    ChatChannel, ChatMember, ChatMessage, MessageReaction, 
    DirectMessage, OnlineStatus
)
from app.modules.project_management.core.schemas.chat_schemas import (
    ChatChannelCreate, ChatChannelUpdate, ChatChannelFilterParams,
    ChatMemberCreate, ChatMemberUpdate,
    ChatMessageCreate, ChatMessageUpdate, ChatMessageFilterParams,
    MessageReactionCreate,
    DirectMessageCreate,
    OnlineStatusUpdate,
    BulkMemberAddRequest, BulkMemberRemoveRequest
)
from app.modules.project_management.events.chat_events import (
    ChatEventDispatcher, ChannelCreatedEvent, MessageSentEvent,
    MemberJoinedEvent, ReactionAddedEvent
)

logger = logging.getLogger(__name__)

class ChatService:
    """Service for handling chat and collaboration operations"""
    
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
            # Create the channel
            channel = ChatChannel(
                name=channel_data.name,
                description=channel_data.description,
                channel_type=channel_data.channel_type.value,
                is_private=channel_data.is_private,
                project_id=channel_data.project_id,
                created_by=created_by
            )
            
            self.db.add(channel)
            await self.db.flush()  # Get the ID
            
            # Add creator as admin
            creator_member = ChatMember(
                channel_id=channel.id,
                employee_id=created_by,
                role="admin",
                joined_at=datetime.utcnow()
            )
            self.db.add(creator_member)
            
            # Add initial members if provided
            if channel_data.member_ids:
                for member_id in channel_data.member_ids:
                    if member_id != created_by:  # Don't add creator twice
                        member = ChatMember(
                            channel_id=channel.id,
                            employee_id=member_id,
                            role="member",
                            joined_at=datetime.utcnow()
                        )
                        self.db.add(member)
            
            await self.db.commit()
            await self.db.refresh(channel)
            
            # Dispatch event
            await self.event_dispatcher.dispatch(ChannelCreatedEvent(
                channel_id=channel.id,
                channel_name=channel.name,
                created_by=created_by,
                member_count=len(channel_data.member_ids or []) + 1
            ))
            
            return channel
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating channel: {str(e)}")
            raise
    
    async def get_channel_by_id(self, channel_id: UUID) -> Optional[ChatChannel]:
        """Get a chat channel by ID"""
        try:
            query = select(ChatChannel).where(
                and_(
                    ChatChannel.id == channel_id,
                    ChatChannel.is_active == True
                )
            ).options(
                selectinload(ChatChannel.members),
                selectinload(ChatChannel.messages)
            )
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting channel {channel_id}: {str(e)}")
            raise
    
    async def list_channels(
        self,
        user_id: UUID,
        filters: Optional[ChatChannelFilterParams] = None,
        page: int = 1,
        size: int = 20,
        sort_by: str = "updated_at",
        sort_desc: bool = True
    ) -> Tuple[List[ChatChannel], int]:
        """List chat channels accessible to the user"""
        try:
            # Base query - user must be a member or channel must be public
            base_query = select(ChatChannel).join(ChatMember).where(
                and_(
                    ChatChannel.is_active == True,
                    or_(
                        and_(ChatMember.employee_id == user_id, ChatMember.is_active == True),
                        ChatChannel.is_private == False
                    )
                )
            )
            
            # Apply filters
            if filters:
                if filters.channel_type:
                    base_query = base_query.where(ChatChannel.channel_type == filters.channel_type.value)
                if filters.is_private is not None:
                    base_query = base_query.where(ChatChannel.is_private == filters.is_private)
                if filters.is_archived is not None:
                    base_query = base_query.where(ChatChannel.is_archived == filters.is_archived)
                if filters.project_id:
                    base_query = base_query.where(ChatChannel.project_id == filters.project_id)
                if filters.created_by:
                    base_query = base_query.where(ChatChannel.created_by == filters.created_by)
            
            # Count total
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply sorting
            sort_column = getattr(ChatChannel, sort_by, ChatChannel.updated_at)
            if sort_desc:
                base_query = base_query.order_by(desc(sort_column))
            else:
                base_query = base_query.order_by(asc(sort_column))
            
            # Apply pagination
            offset = (page - 1) * size
            query = base_query.offset(offset).limit(size)
            
            result = await self.db.execute(query)
            channels = result.scalars().unique().all()
            
            return list(channels), total
            
        except Exception as e:
            logger.error(f"Error listing channels: {str(e)}")
            raise
    
    async def update_channel(
        self,
        channel_id: UUID,
        channel_data: ChatChannelUpdate,
        user_id: UUID
    ) -> Optional[ChatChannel]:
        """Update a chat channel"""
        try:
            # Check if user has permission (admin or moderator)
            member_query = select(ChatMember).where(
                and_(
                    ChatMember.channel_id == channel_id,
                    ChatMember.employee_id == user_id,
                    ChatMember.role.in_(["admin", "moderator"]),
                    ChatMember.is_active == True
                )
            )
            member_result = await self.db.execute(member_query)
            member = member_result.scalar_one_or_none()
            
            if not member:
                raise PermissionError("User does not have permission to update this channel")
            
            # Update channel
            update_data = {k: v for k, v in channel_data.dict(exclude_unset=True).items() if v is not None}
            update_data['updated_at'] = datetime.utcnow()
            update_data['updated_by'] = user_id
            
            query = update(ChatChannel).where(ChatChannel.id == channel_id).values(**update_data)
            await self.db.execute(query)
            await self.db.commit()
            
            # Return updated channel
            return await self.get_channel_by_id(channel_id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating channel {channel_id}: {str(e)}")
            raise
    
    async def delete_channel(self, channel_id: UUID, user_id: UUID) -> bool:
        """Delete (soft delete) a chat channel"""
        try:
            # Check if user is admin
            member_query = select(ChatMember).where(
                and_(
                    ChatMember.channel_id == channel_id,
                    ChatMember.employee_id == user_id,
                    ChatMember.role == "admin",
                    ChatMember.is_active == True
                )
            )
            member_result = await self.db.execute(member_query)
            member = member_result.scalar_one_or_none()
            
            if not member:
                raise PermissionError("User does not have permission to delete this channel")
            
            # Soft delete
            query = update(ChatChannel).where(ChatChannel.id == channel_id).values(
                is_active=False,
                updated_at=datetime.utcnow(),
                updated_by=user_id
            )
            await self.db.execute(query)
            await self.db.commit()
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting channel {channel_id}: {str(e)}")
            raise
    
    # ================================
    # Chat Member Operations
    # ================================
    
    async def add_member(
        self,
        channel_id: UUID,
        member_data: ChatMemberCreate,
        added_by: UUID
    ) -> ChatMember:
        """Add a member to a chat channel"""
        try:
            # Check if user has permission to add members
            admin_query = select(ChatMember).where(
                and_(
                    ChatMember.channel_id == channel_id,
                    ChatMember.employee_id == added_by,
                    ChatMember.role.in_(["admin", "moderator"]),
                    ChatMember.is_active == True
                )
            )
            admin_result = await self.db.execute(admin_query)
            admin = admin_result.scalar_one_or_none()
            
            if not admin:
                raise PermissionError("User does not have permission to add members")
            
            # Check if member already exists
            existing_query = select(ChatMember).where(
                and_(
                    ChatMember.channel_id == channel_id,
                    ChatMember.employee_id == member_data.employee_id
                )
            )
            existing_result = await self.db.execute(existing_query)
            existing_member = existing_result.scalar_one_or_none()
            
            if existing_member:
                if existing_member.is_active:
                    raise ValueError("Member is already in the channel")
                else:
                    # Reactivate existing member
                    query = update(ChatMember).where(ChatMember.id == existing_member.id).values(
                        is_active=True,
                        role=member_data.role.value,
                        joined_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        updated_by=added_by
                    )
                    await self.db.execute(query)
                    await self.db.commit()
                    
                    await self.db.refresh(existing_member)
                    return existing_member
            
            # Create new member
            member = ChatMember(
                channel_id=member_data.channel_id,
                employee_id=member_data.employee_id,
                role=member_data.role.value,
                joined_at=datetime.utcnow(),
                created_by=added_by
            )
            
            self.db.add(member)
            await self.db.commit()
            await self.db.refresh(member)
            
            # Dispatch event
            await self.event_dispatcher.dispatch(MemberJoinedEvent(
                channel_id=channel_id,
                employee_id=member_data.employee_id,
                added_by=added_by
            ))
            
            return member
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding member to channel {channel_id}: {str(e)}")
            raise
    
    async def remove_member(
        self,
        channel_id: UUID,
        employee_id: UUID,
        removed_by: UUID
    ) -> bool:
        """Remove a member from a chat channel"""
        try:
            # Check permissions
            admin_query = select(ChatMember).where(
                and_(
                    ChatMember.channel_id == channel_id,
                    ChatMember.employee_id == removed_by,
                    ChatMember.role.in_(["admin", "moderator"]),
                    ChatMember.is_active == True
                )
            )
            admin_result = await self.db.execute(admin_query)
            admin = admin_result.scalar_one_or_none()
            
            if not admin and removed_by != employee_id:  # Users can remove themselves
                raise PermissionError("User does not have permission to remove members")
            
            # Remove member (soft delete)
            query = update(ChatMember).where(
                and_(
                    ChatMember.channel_id == channel_id,
                    ChatMember.employee_id == employee_id
                )
            ).values(
                is_active=False,
                updated_at=datetime.utcnow(),
                updated_by=removed_by
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error removing member from channel {channel_id}: {str(e)}")
            raise
    
    async def bulk_add_members(
        self,
        channel_id: UUID,
        request: BulkMemberAddRequest,
        added_by: UUID
    ) -> Dict[str, Any]:
        """Bulk add members to a channel"""
        try:
            success_count = 0
            failed_count = 0
            errors = []
            
            for employee_id in request.employee_ids:
                try:
                    member_data = ChatMemberCreate(
                        channel_id=channel_id,
                        employee_id=employee_id,
                        role=request.role
                    )
                    await self.add_member(channel_id, member_data, added_by)
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Failed to add {employee_id}: {str(e)}")
            
            return {
                "success_count": success_count,
                "failed_count": failed_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error in bulk add members: {str(e)}")
            raise
    
    # ================================
    # Chat Message Operations
    # ================================
    
    async def send_message(
        self,
        message_data: ChatMessageCreate,
        sender_id: UUID
    ) -> ChatMessage:
        """Send a message to a chat channel"""
        try:
            # Verify user is a member of the channel
            member_query = select(ChatMember).where(
                and_(
                    ChatMember.channel_id == message_data.channel_id,
                    ChatMember.employee_id == sender_id,
                    ChatMember.is_active == True
                )
            )
            member_result = await self.db.execute(member_query)
            member = member_result.scalar_one_or_none()
            
            if not member:
                raise PermissionError("User is not a member of this channel")
            
            # Create message
            message = ChatMessage(
                content=message_data.content,
                message_type=message_data.message_type.value,
                channel_id=message_data.channel_id,
                sender_id=sender_id,
                parent_message_id=message_data.parent_message_id,
                mentioned_users=message_data.mentioned_users,
                attachments=message_data.attachments,
                created_by=sender_id
            )
            
            self.db.add(message)
            
            # Update thread count if this is a reply
            if message_data.parent_message_id:
                thread_update = update(ChatMessage).where(
                    ChatMessage.id == message_data.parent_message_id
                ).values(
                    thread_count=ChatMessage.thread_count + 1
                )
                await self.db.execute(thread_update)
            
            # Update channel's last message time
            channel_update = update(ChatChannel).where(
                ChatChannel.id == message_data.channel_id
            ).values(
                last_message_at=datetime.utcnow(),
                message_count=ChatChannel.message_count + 1
            )
            await self.db.execute(channel_update)
            
            await self.db.commit()
            await self.db.refresh(message)
            
            # Dispatch event
            await self.event_dispatcher.dispatch(MessageSentEvent(
                message_id=message.id,
                channel_id=message_data.channel_id,
                sender_id=sender_id,
                content=message_data.content,
                mentioned_users=message_data.mentioned_users or []
            ))
            
            return message
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error sending message: {str(e)}")
            raise
    
    async def get_channel_messages(
        self,
        channel_id: UUID,
        user_id: UUID,
        filters: Optional[ChatMessageFilterParams] = None,
        page: int = 1,
        size: int = 50,
        sort_desc: bool = True
    ) -> Tuple[List[ChatMessage], int]:
        """Get messages from a chat channel"""
        try:
            # Verify user is a member
            member_query = select(ChatMember).where(
                and_(
                    ChatMember.channel_id == channel_id,
                    ChatMember.employee_id == user_id,
                    ChatMember.is_active == True
                )
            )
            member_result = await self.db.execute(member_query)
            member = member_result.scalar_one_or_none()
            
            if not member:
                raise PermissionError("User is not a member of this channel")
            
            # Build query
            base_query = select(ChatMessage).where(
                and_(
                    ChatMessage.channel_id == channel_id,
                    ChatMessage.is_active == True,
                    ChatMessage.parent_message_id.is_(None)  # Only top-level messages
                )
            )
            
            # Apply filters
            if filters:
                if filters.message_type:
                    base_query = base_query.where(ChatMessage.message_type == filters.message_type.value)
                if filters.sender_id:
                    base_query = base_query.where(ChatMessage.sender_id == filters.sender_id)
                if filters.has_attachments is not None:
                    if filters.has_attachments:
                        base_query = base_query.where(ChatMessage.attachments.isnot(None))
                    else:
                        base_query = base_query.where(ChatMessage.attachments.is_(None))
                if filters.is_pinned is not None:
                    base_query = base_query.where(ChatMessage.is_pinned == filters.is_pinned)
                if filters.date_from:
                    base_query = base_query.where(ChatMessage.created_at >= filters.date_from)
                if filters.date_to:
                    base_query = base_query.where(ChatMessage.created_at <= filters.date_to)
            
            # Count total
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply sorting and pagination
            if sort_desc:
                base_query = base_query.order_by(desc(ChatMessage.created_at))
            else:
                base_query = base_query.order_by(asc(ChatMessage.created_at))
            
            offset = (page - 1) * size
            query = base_query.offset(offset).limit(size).options(
                selectinload(ChatMessage.reactions)
            )
            
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            return list(messages), total
            
        except Exception as e:
            logger.error(f"Error getting channel messages: {str(e)}")
            raise
    
    async def update_message(
        self,
        message_id: UUID,
        message_data: ChatMessageUpdate,
        user_id: UUID
    ) -> Optional[ChatMessage]:
        """Update a chat message"""
        try:
            # Get message and verify ownership
            message_query = select(ChatMessage).where(ChatMessage.id == message_id)
            message_result = await self.db.execute(message_query)
            message = message_result.scalar_one_or_none()
            
            if not message:
                return None
            
            if message.sender_id != user_id:
                raise PermissionError("User can only edit their own messages")
            
            # Check if message is too old to edit (24 hours)
            if datetime.utcnow() - message.created_at > timedelta(hours=24):
                raise ValueError("Message is too old to edit")
            
            # Update message
            query = update(ChatMessage).where(ChatMessage.id == message_id).values(
                content=message_data.content,
                is_edited=True,
                updated_at=datetime.utcnow(),
                updated_by=user_id
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Return updated message
            updated_result = await self.db.execute(message_query)
            return updated_result.scalar_one_or_none()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating message {message_id}: {str(e)}")
            raise
    
    async def delete_message(self, message_id: UUID, user_id: UUID) -> bool:
        """Delete a chat message"""
        try:
            # Get message and verify ownership or admin rights
            message_query = select(ChatMessage).join(ChatMember).where(
                and_(
                    ChatMessage.id == message_id,
                    or_(
                        ChatMessage.sender_id == user_id,  # Own message
                        and_(  # Channel admin/moderator
                            ChatMember.channel_id == ChatMessage.channel_id,
                            ChatMember.employee_id == user_id,
                            ChatMember.role.in_(["admin", "moderator"]),
                            ChatMember.is_active == True
                        )
                    )
                )
            )
            message_result = await self.db.execute(message_query)
            message = message_result.scalar_one_or_none()
            
            if not message:
                raise PermissionError("User cannot delete this message")
            
            # Soft delete
            query = update(ChatMessage).where(ChatMessage.id == message_id).values(
                is_active=False,
                updated_at=datetime.utcnow(),
                updated_by=user_id
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting message {message_id}: {str(e)}")
            raise
    
    # ================================
    # Message Reaction Operations
    # ================================
    
    async def add_reaction(
        self,
        reaction_data: MessageReactionCreate,
        user_id: UUID
    ) -> MessageReaction:
        """Add a reaction to a message"""
        try:
            # Check if user already reacted with this emoji
            existing_query = select(MessageReaction).where(
                and_(
                    MessageReaction.message_id == reaction_data.message_id,
                    MessageReaction.employee_id == user_id,
                    MessageReaction.emoji == reaction_data.emoji,
                    MessageReaction.is_active == True
                )
            )
            existing_result = await self.db.execute(existing_query)
            existing_reaction = existing_result.scalar_one_or_none()
            
            if existing_reaction:
                return existing_reaction
            
            # Create new reaction
            reaction = MessageReaction(
                message_id=reaction_data.message_id,
                employee_id=user_id,
                emoji=reaction_data.emoji,
                created_by=user_id
            )
            
            self.db.add(reaction)
            await self.db.commit()
            await self.db.refresh(reaction)
            
            # Dispatch event
            await self.event_dispatcher.dispatch(ReactionAddedEvent(
                message_id=reaction_data.message_id,
                employee_id=user_id,
                emoji=reaction_data.emoji
            ))
            
            return reaction
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding reaction: {str(e)}")
            raise
    
    async def remove_reaction(
        self,
        message_id: UUID,
        emoji: str,
        user_id: UUID
    ) -> bool:
        """Remove a reaction from a message"""
        try:
            query = update(MessageReaction).where(
                and_(
                    MessageReaction.message_id == message_id,
                    MessageReaction.employee_id == user_id,
                    MessageReaction.emoji == emoji
                )
            ).values(
                is_active=False,
                updated_at=datetime.utcnow(),
                updated_by=user_id
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error removing reaction: {str(e)}")
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
            
            message = DirectMessage(
                content=message_data.content,
                message_type=message_data.message_type.value,
                sender_id=sender_id,
                recipient_id=message_data.recipient_id,
                attachments=message_data.attachments,
                created_by=sender_id
            )
            
            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)
            
            return message
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error sending direct message: {str(e)}")
            raise
    
    async def get_direct_messages(
        self,
        user_id: UUID,
        other_user_id: UUID,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[DirectMessage], int]:
        """Get direct messages between two users"""
        try:
            base_query = select(DirectMessage).where(
                and_(
                    DirectMessage.is_active == True,
                    or_(
                        and_(
                            DirectMessage.sender_id == user_id,
                            DirectMessage.recipient_id == other_user_id
                        ),
                        and_(
                            DirectMessage.sender_id == other_user_id,
                            DirectMessage.recipient_id == user_id
                        )
                    )
                )
            )
            
            # Count total
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and sorting
            offset = (page - 1) * size
            query = base_query.order_by(desc(DirectMessage.created_at)).offset(offset).limit(size)
            
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            return list(messages), total
            
        except Exception as e:
            logger.error(f"Error getting direct messages: {str(e)}")
            raise
    
    async def mark_direct_message_as_read(
        self,
        message_id: UUID,
        user_id: UUID
    ) -> bool:
        """Mark a direct message as read"""
        try:
            query = update(DirectMessage).where(
                and_(
                    DirectMessage.id == message_id,
                    DirectMessage.recipient_id == user_id,
                    DirectMessage.is_read == False
                )
            ).values(
                is_read=True,
                read_at=datetime.utcnow()
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error marking message as read: {str(e)}")
            raise
    
    # ================================
    # Online Status Operations
    # ================================
    
    async def update_online_status(
        self,
        user_id: UUID,
        status_data: OnlineStatusUpdate
    ) -> OnlineStatus:
        """Update user's online status"""
        try:
            # Check if status record exists
            existing_query = select(OnlineStatus).where(OnlineStatus.employee_id == user_id)
            existing_result = await self.db.execute(existing_query)
            existing_status = existing_result.scalar_one_or_none()
            
            if existing_status:
                # Update existing status
                query = update(OnlineStatus).where(OnlineStatus.employee_id == user_id).values(
                    status=status_data.status.value,
                    custom_status=status_data.custom_status,
                    last_seen=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    updated_by=user_id
                )
                await self.db.execute(query)
                await self.db.commit()
                
                # Return updated status
                updated_result = await self.db.execute(existing_query)
                return updated_result.scalar_one()
            else:
                # Create new status
                status = OnlineStatus(
                    employee_id=user_id,
                    status=status_data.status.value,
                    custom_status=status_data.custom_status,
                    last_seen=datetime.utcnow(),
                    created_by=user_id
                )
                
                self.db.add(status)
                await self.db.commit()
                await self.db.refresh(status)
                
                return status
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating online status: {str(e)}")
            raise
    
    async def get_online_users(self, limit: int = 100) -> List[OnlineStatus]:
        """Get list of online users"""
        try:
            # Consider users online if they were active in last 5 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            
            query = select(OnlineStatus).where(
                and_(
                    OnlineStatus.status.in_(["online", "away", "busy"]),
                    OnlineStatus.last_seen >= cutoff_time,
                    OnlineStatus.is_active == True
                )
            ).order_by(desc(OnlineStatus.last_seen)).limit(limit)
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting online users: {str(e)}")
            raise
    
    async def update_last_seen(self, user_id: UUID) -> None:
        """Update user's last seen timestamp"""
        try:
            query = update(OnlineStatus).where(OnlineStatus.employee_id == user_id).values(
                last_seen=datetime.utcnow()
            )
            await self.db.execute(query)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating last seen for user {user_id}: {str(e)}")
            # Don't raise here as this is a background operation
