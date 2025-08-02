# app/modules/project_management/core/schemas/__init__.py


from .project_schemas import *
from .project_task_schemas import TaskCreate, TaskUpdate, TaskOut

__all__ = [
    # Project schemas
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectOut",
    "ProjectListResponse",
    "ProjectMemberCreate",
    "ProjectMemberResponse",
    
    # Task schemas
    "TaskCreate",
    "TaskUpdate",
    "TaskOut",
    "TaskCommentCreate",
    "TaskCommentResponse",
    
    # Time tracking schemas
    "TimeEntryCreate",
    "TimeEntryUpdate",
    "TimeEntryResponse",
    "WorkSessionCreate",
    "WorkSessionResponse",
    
    # Calendar schemas
    "CalendarEventCreate",
    "CalendarEventUpdate",
    "CalendarEventResponse",
    "ReminderCreate",
    "ReminderResponse",
    
    # Notification schemas
    "NotificationCreate",
    "NotificationResponse",
    "UserNotificationPreferenceUpdate",
    "UserNotificationPreferenceResponse",
    
    # Report schemas
    "ReportCreate",
    "ReportResponse",
    "ReportDataResponse",
]
