# app/modules/project_management/config.py
"""Configuration settings for Project Management module"""
from enum import Enum
from typing import Dict, List


class ProjectStatus(Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ProjectEventTypes:
    """Event types for Project Management module"""
    
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_STATUS_CHANGED = "project.status_changed"
    PROJECT_DELETED = "project.deleted"
    PROJECT_BUDGET_EXCEEDED = "project.budget_exceeded"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_ASSIGNED = "task.assigned"
    TASK_COMPLETED = "task.completed"
    TASK_OVERDUE = "task.overdue"
    
    # Milestone events
    MILESTONE_CREATED = "milestone.created"
    MILESTONE_COMPLETED = "milestone.completed"
    MILESTONE_OVERDUE = "milestone.overdue"
    
    # Timeline events
    PHASE_STARTED = "phase.started"
    PHASE_COMPLETED = "phase.completed"
    DEADLINE_APPROACHING = "deadline.approaching"
    
    # Calendar events
    CALENDAR_EVENT_CREATED = "calendar.event.created"
    CALENDAR_CONFLICT_DETECTED = "calendar.conflict.detected"
    MEETING_REMINDER = "meeting.reminder"
    
    # Resource events
    RESOURCE_ALLOCATED = "resource.allocated"
    RESOURCE_OVERALLOCATED = "resource.overallocated"
    TEAM_MEMBER_ADDED = "team.member.added"
    
    # Communication events
    PROJECT_MESSAGE_SENT = "project.message.sent"
    COMMENT_ADDED = "comment.added"
    NOTIFICATION_SENT = "notification.sent"


class ModuleConfig:
    """Configuration constants for Project Management module"""
    
    # Database table prefix
    TABLE_PREFIX = "pm_"
    
    # Default settings
    DEFAULT_TASK_ESTIMATED_HOURS = 8
    DEFAULT_PROJECT_BUFFER_PERCENTAGE = 20
    
    # Notification settings
    DEADLINE_WARNING_DAYS = [1, 3, 7]  # Days before deadline to send warnings
    OVERDUE_REMINDER_HOURS = [24, 72, 168]  # Hours after overdue to send reminders
    
    # Calendar settings
    DEFAULT_MEETING_DURATION_MINUTES = 60
    DEFAULT_WORKING_HOURS_START = 9  # 9 AM
    DEFAULT_WORKING_HOURS_END = 17   # 5 PM
    
    # File upload settings
    MAX_FILE_SIZE_MB = 50
    ALLOWED_FILE_TYPES = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.jpg', '.png', '.gif']
    
    # Integration settings
    SLACK_WEBHOOK_TIMEOUT = 30
    EMAIL_NOTIFICATION_BATCH_SIZE = 100
    
    # Performance settings
    MAX_PROJECTS_PER_PAGE = 50
    MAX_TASKS_PER_PROJECT = 1000
    CACHE_TIMEOUT_SECONDS = 300


class CalendarEventTypes(Enum):
    """Types of calendar events"""
    MEETING = "meeting"
    MILESTONE = "milestone"
    DEADLINE = "deadline"
    PERSONAL = "personal"
    HOLIDAY = "holiday"
    TRAINING = "training"
    IMPORTED = "imported"


class NotificationTypes(Enum):
    """Types of notifications"""
    TASK_ASSIGNED = "task_assigned"
    TASK_OVERDUE = "task_overdue"
    MILESTONE_REMINDER = "milestone_reminder"
    DEADLINE_WARNING = "deadline_warning"
    PROJECT_STATUS_CHANGE = "project_status_change"
    MEETING_REMINDER = "meeting_reminder"
    CALENDAR_CONFLICT = "calendar_conflict"
    BUDGET_ALERT = "budget_alert"
    # Chat notifications
    CHAT_MESSAGE_RECEIVED = "chat_message_received"
    CHAT_MEMBER_ADDED = "chat_member_added"
    CHAT_MEMBER_REMOVED = "chat_member_removed"
    DIRECT_MESSAGE_RECEIVED = "direct_message_received"


class ChatPermissions(Enum):
    """Chat and collaboration permissions"""
    # Channel permissions
    CREATE_CHANNEL = "chat:create_channel"
    VIEW_CHANNEL = "chat:view_channel"
    EDIT_CHANNEL = "chat:edit_channel"
    DELETE_CHANNEL = "chat:delete_channel"
    ARCHIVE_CHANNEL = "chat:archive_channel"
    
    # Member permissions
    ADD_MEMBER = "chat:add_member"
    REMOVE_MEMBER = "chat:remove_member"
    MANAGE_ROLES = "chat:manage_roles"
    VIEW_MEMBERS = "chat:view_members"
    
    # Message permissions
    SEND_MESSAGE = "chat:send_message"
    EDIT_MESSAGE = "chat:edit_message"
    DELETE_MESSAGE = "chat:delete_message"
    VIEW_MESSAGES = "chat:view_messages"
    PIN_MESSAGE = "chat:pin_message"
    
    # Reaction permissions
    ADD_REACTION = "chat:add_reaction"
    REMOVE_REACTION = "chat:remove_reaction"
    VIEW_REACTIONS = "chat:view_reactions"
    
    # Direct message permissions
    SEND_DIRECT_MESSAGE = "chat:send_direct_message"
    VIEW_DIRECT_MESSAGES = "chat:view_direct_messages"
    
    # Admin permissions
    MODERATE_CHAT = "chat:moderate"
    VIEW_ANALYTICS = "chat:view_analytics"


# API Endpoint configurations
API_ENDPOINTS = {
    "projects": [
        "GET /project-management/projects/",
        "POST /project-management/projects/",
        "GET /project-management/projects/{id}",
        "PUT /project-management/projects/{id}",
        "DELETE /project-management/projects/{id}",
        "GET /project-management/projects/{id}/tasks/",
        "GET /project-management/projects/{id}/budget/",
        "POST /project-management/projects/{id}/team-members/",
    ],
    "tasks": [
        "GET /project-management/tasks/",
        "POST /project-management/tasks/",
        "PUT /project-management/tasks/{id}",
        "DELETE /project-management/tasks/{id}",
        "POST /project-management/tasks/{id}/comments/",
        "GET /project-management/tasks/{id}/time-logs/",
    ],
    "calendar": [
        "POST /project-management/calendar/events/",
        "GET /project-management/calendar/events/",
        "PUT /project-management/calendar/events/{id}",
        "DELETE /project-management/calendar/events/{id}",
        "GET /project-management/calendar/conflicts/",
        "POST /project-management/calendar/sync/",
    ],
    "timeline": [
        "GET /project-management/projects/{id}/timeline/",
        "POST /project-management/projects/{id}/phases/",
        "PUT /project-management/phases/{id}",
        "POST /project-management/milestones/",
        "PUT /project-management/milestones/{id}/complete",
    ],
    "analytics": [
        "GET /project-management/analytics/dashboard/",
        "GET /project-management/analytics/productivity/",
        "GET /project-management/analytics/budget-utilization/",
        "GET /project-management/analytics/team-performance/",
    ],
    "chat": [
        "GET /project-management/chat/channels/",
        "POST /project-management/chat/channels/",
        "GET /project-management/chat/channels/{channel_id}",
        "PUT /project-management/chat/channels/{channel_id}",
        "DELETE /project-management/chat/channels/{channel_id}",
        "POST /project-management/chat/channels/{channel_id}/archive",
        "POST /project-management/chat/channels/{channel_id}/restore",
        
        "GET /project-management/chat/channels/{channel_id}/members/",
        "POST /project-management/chat/channels/{channel_id}/members/",
        "PUT /project-management/chat/channels/{channel_id}/members/{member_id}",
        "DELETE /project-management/chat/channels/{channel_id}/members/{member_id}",
        "POST /project-management/chat/channels/{channel_id}/members/bulk",
        
        "GET /project-management/chat/channels/{channel_id}/messages/",
        "POST /project-management/chat/channels/{channel_id}/messages/",
        "PUT /project-management/chat/messages/{message_id}",
        "DELETE /project-management/chat/messages/{message_id}",
        "POST /project-management/chat/messages/{message_id}/pin",
        "DELETE /project-management/chat/messages/{message_id}/pin",
        
        "POST /project-management/chat/messages/{message_id}/reactions/",
        "DELETE /project-management/chat/messages/{message_id}/reactions/{reaction_id}",
        
        "GET /project-management/chat/direct-messages/",
        "POST /project-management/chat/direct-messages/",
        "GET /project-management/chat/direct-messages/{conversation_id}",
        "PUT /project-management/chat/direct-messages/{message_id}",
        "DELETE /project-management/chat/direct-messages/{message_id}",
        
        "GET /project-management/chat/online-status/",
        "PUT /project-management/chat/online-status/",
        "GET /project-management/chat/users/{user_id}/status",
        
        "WS /project-management/chat/ws",
    ]
}
