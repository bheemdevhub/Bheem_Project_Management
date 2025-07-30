from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from bheem_core.modules.project_management.config import ProjectStatus, TaskStatus, Priority, CalendarEventTypes, NotificationTypes

# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        use_enum_values = True

# Project schemas
class ProjectBase(BaseSchema):
    """Base project schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget_allocated: Optional[Decimal] = Field(None, ge=0)
    project_manager_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProjectCreate(ProjectBase):
    """Schema for creating a project"""
    company_id: Optional[UUID] = None
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v and values.get('start_date') and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class ProjectUpdate(BaseSchema):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[Priority] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget_allocated: Optional[Decimal] = Field(None, ge=0)
    project_manager_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    is_archived: Optional[bool] = None

class ProjectResponse(ProjectBase):
    id: Optional[UUID] = None
    status: Optional[ProjectStatus] = None
    completion_percentage: Optional[int] = 0
    health_score: Optional[int] = None
    risk_level: Optional[str] = None
    budget_spent: Optional[Decimal] = Decimal("0.0")
    budget_remaining: Optional[Decimal] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    is_template: Optional[bool] = False
    is_archived: Optional[bool] = False
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
# app/modules/project_management/core/schemas/project_schemas.py






# Alias for compatibility with older imports
ProjectOut = ProjectResponse

# Task schemas
class TaskBase(BaseSchema):
    """Base task schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    estimated_hours: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class TaskCreate(TaskBase):
    """Schema for creating a task"""
    project_id: UUID
    phase_id: UUID
    assigned_to: UUID
    parent_task_id: UUID
    is_milestone: bool = False


class TaskUpdate(BaseSchema):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    estimated_hours: Optional[Decimal] = Field(None, ge=0)
    actual_hours: Optional[Decimal] = Field(None, ge=0)
    remaining_hours: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    assigned_to: UUID
    phase_id: UUID
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class TaskResponse(TaskBase):
    """Schema for task responses"""
    id: UUID
    status: TaskStatus
    project_id: UUID
    phase_id: UUID
    assigned_to: UUID
    actual_hours: Decimal
    remaining_hours: Optional[Decimal]
    completion_percentage: int
    completed_date: Optional[datetime]
    parent_task_id: UUID 
    is_milestone: bool
    created_by : UUID
    created_at: datetime
    updated_at: datetime


class TaskAssignment(BaseSchema):
    """Schema for task assignment"""
    assignee_id: UUID
    due_date: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = Field(None, ge=0)


# Project Phase schemas
class ProjectPhaseBase(BaseSchema):
    """Base project phase schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    order_sequence: int = Field(..., ge=1)
    dependencies: Optional[List[int]] = None  # List of phase IDs


class ProjectPhaseCreate(ProjectPhaseBase):
    """Schema for creating a project phase"""
    project_id: UUID


class ProjectPhaseUpdate(BaseSchema):
    """Schema for updating a project phase"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = None
    dependencies: Optional[List[int]] = None


class ProjectPhaseResponse(ProjectPhaseBase):
    """Schema for project phase responses"""
    id: UUID
    project_id: UUID
    completion_percentage: int
    status: str
    actual_start_date: Optional[datetime]
    actual_end_date: Optional[datetime]
    created_by : UUID
    created_at: datetime
    updated_at: datetime


# Milestone schemas
class ProjectMilestoneBase(BaseSchema):
    """Base milestone schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: datetime
    is_critical: bool = False
    responsible_employee_id: UUID


class ProjectMilestoneCreate(ProjectMilestoneBase):
    """Schema for creating a milestone"""
    project_id: UUID
    phase_id: UUID


class ProjectMilestoneUpdate(BaseSchema):
    """Schema for updating a milestone"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    is_completed: Optional[bool] = None
    is_critical: Optional[bool] = None
    responsible_employee_id: UUID


class ProjectMilestoneResponse(ProjectMilestoneBase):
    """Schema for milestone responses"""
    id: UUID
    project_id: UUID
    phase_id: UUID
    is_completed: bool
    completion_date: Optional[datetime]
    created_by : UUID
    created_at: datetime
    updated_at: datetime


# Calendar schemas
class UniversalCalendarBase(BaseSchema):
    """Base calendar event schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[str] = None
    attendee_ids: Optional[List[int]] = None
    reminder_minutes: Optional[List[int]] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    url: Optional[str] = None
    
    @validator('end_datetime')
    def end_after_start(cls, v, values):
        if v and values.get('start_datetime') and v <= values['start_datetime']:
            raise ValueError('End time must be after start time')
        return v


class UniversalCalendarCreate(UniversalCalendarBase):
    """Schema for creating a calendar event"""
    event_type: CalendarEventTypes
    project_id: UUID
    task_id: UUID
    milestone_id: UUID
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    visibility: str = "public"
    priority: Priority = Priority.MEDIUM


class UniversalCalendarUpdate(BaseSchema):
    """Schema for updating a calendar event"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    attendee_ids: Optional[List[int]] = None
    status: Optional[str] = None
    visibility: Optional[str] = None
    priority: Optional[Priority] = None
    reminder_minutes: Optional[List[int]] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    url: Optional[str] = None


class UniversalCalendarResponse(UniversalCalendarBase):
    """Schema for calendar event responses"""
    id: UUID
    event_type: CalendarEventTypes
    project_id: UUID
    task_id: UUID
    milestone_id: UUID
    is_recurring: bool
    recurrence_rule: Optional[str]
    status: str
    visibility: str
    priority: Priority
    attendee_responses: Optional[Dict[str, str]]
    external_event_id: UUID 
    external_calendar_source: Optional[str]
    created_by : UUID
    created_at: datetime
    updated_at: datetime


class EventResponse(BaseSchema):
    """Schema for responding to calendar events"""
    response: str = Field(..., pattern=r'^(accepted|declined|tentative)$')
    comment: Optional[str] = None


# Time Log schemas
class TimeLogBase(BaseSchema):
    """Base time log schema"""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_hours: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    activity_type: Optional[str] = None
    is_billable: bool = True
    hourly_rate: Optional[Decimal] = Field(None, ge=0)


class TimeLogCreate(TimeLogBase):
    """Schema for creating a time log"""
    task_id: UUID
    employee_id: UUID
    project_id: UUID


class TimeLogUpdate(BaseSchema):
    """Schema for updating a time log"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_hours: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    activity_type: Optional[str] = None
    is_billable: Optional[bool] = None
    hourly_rate: Optional[Decimal] = Field(None, ge=0)


class TimeLogResponse(TimeLogBase):
    """Schema for time log responses"""
    id: UUID
    task_id: UUID
    employee_id: UUID
    project_id: UUID
    billable_amount: Optional[Decimal]
    is_approved: bool
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# Comment schemas
class CommentBase(BaseSchema):
    """Base comment schema"""
    content: str = Field(..., min_length=1)
    mentioned_users: Optional[List[int]] = None
    attachments: Optional[List[str]] = None


class CommentCreate(CommentBase):
    """Schema for creating a comment"""
    comment_type: str = Field(..., pattern=r'^(project|task|milestone)$')
    project_id: UUID
    task_id: UUID
    milestone_id: UUID
    parent_comment_id: UUID


class CommentUpdate(BaseSchema):
    """Schema for updating a comment"""
    content: Optional[str] = Field(None, min_length=1)
    mentioned_users: Optional[List[int]] = None
    attachments: Optional[List[str]] = None


class CommentResponse(CommentBase):
    """Schema for comment responses"""
    id: UUID
    comment_type: str
    project_id: UUID
    task_id: UUID
    milestone_id: UUID
    parent_comment_id: UUID
    author_id: UUID
    is_edited: bool
    created_at: datetime
    updated_at: datetime


# Notification schemas
class NotificationResponse(BaseSchema):
    """Schema for notification responses"""
    id: UUID
    recipient_id: UUID
    sender_id: UUID 
    notification_type: NotificationTypes
    title: str
    content: str
    related_entity_type: Optional[str]
    related_entity_id: UUID 
    is_read: bool
    read_at: Optional[datetime]
    priority: Priority
    action_url: Optional[str]
    meta: Optional[Dict[str, Any]]
    created_at: datetime
    expires_at: Optional[datetime]


# Alert schemas
class DeadlineAlertResponse(BaseSchema):
    """Schema for deadline alert responses"""
    id: UUID
    entity_type: str
    entity_id: UUID
    alert_type: str
    alert_date: datetime
    due_date: datetime
    days_difference: int
    is_acknowledged: bool
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]
    created_at: datetime


# Complex response schemas
class ProjectTimelineResponse(BaseSchema):
    """Schema for project timeline responses"""
    project_id: UUID
    project_name: str
    phases: List[ProjectPhaseResponse]
    milestones: List[ProjectMilestoneResponse]
    critical_path: List[int]
    estimated_completion: Optional[datetime]
    actual_completion: Optional[datetime]


class AnalyticsDashboardResponse(BaseSchema):
    """Schema for analytics dashboard"""
    total_projects: int
    active_projects: int
    completed_projects: int
    id: Optional[UUID] = None
    status: Optional[ProjectStatus] = None
    completion_percentage: Optional[int] = 0
    health_score: Optional[int] = None
    risk_level: Optional[str] = None
    budget_spent: Optional[Decimal] = Decimal("0.0")
    budget_remaining: Optional[Decimal] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    is_template: Optional[bool] = False
    is_archived: Optional[bool] = False
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    bottlenecks: List[str]
    top_performers: List[Dict[str, Any]]
    productivity_trend: List[Dict[str, Any]]
    time_allocation: Dict[str, float]


class BudgetUtilizationResponse(BaseSchema):
    """Schema for budget utilization"""
    total_budget: Decimal
    spent_budget: Decimal
    remaining_budget: Decimal
    utilization_percentage: float
    forecast_completion: float
    burn_rate: Decimal
    budget_by_category: Dict[str, Decimal]
    variance_analysis: Dict[str, Any]


class ResourceUtilizationResponse(BaseSchema):
    """Schema for resource utilization"""
    total_resources: int
    allocated_resources: int
    utilization_percentage: float
    overallocated_resources: int
    available_capacity: float
    utilization_by_role: Dict[str, float]
    resource_forecast: List[Dict[str, Any]]


# Team management schemas
class TeamMemberAdd(BaseSchema):
    """Schema for adding team members"""
    employee_id: UUID
    role: str = Field(..., min_length=1, max_length=100)
    allocation_percentage: int = Field(100, ge=1, le=100)
    hourly_rate: Optional[Decimal] = Field(None, ge=0)
    start_date: datetime
    end_date: Optional[datetime] = None
    permissions: Optional[List[str]] = None


class TeamMemberUpdate(BaseSchema):
    """Schema for updating team members"""
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    allocation_percentage: Optional[int] = Field(None, ge=1, le=100)
    hourly_rate: Optional[Decimal] = Field(None, ge=0)
    end_date: Optional[datetime] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TeamMemberResponse(BaseSchema):
    """Schema for team member responses"""
    id: UUID
    project_id: UUID
    employee_id: UUID
    role: str
    allocation_percentage: int
    hourly_rate: Optional[Decimal]
    start_date: datetime
    end_date: Optional[datetime]
    is_active: bool
    permissions: Optional[List[str]]
    created_at: datetime


# Chat and communication schemas
class ChatChannelCreate(BaseSchema):
    """Schema for creating chat channels"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    channel_type: str = Field(..., pattern=r'^(project|team|direct|public)$')
    is_private: bool = False
    project_id: UUID
    member_ids: List[int] = []


class ChatMessageCreate(BaseSchema):
    """Schema for creating chat messages"""
    content: str = Field(..., min_length=1)
    channel_id: UUID
    message_type: str = "text"
    parent_message_id: UUID
    mentioned_users: Optional[List[int]] = None
    attachments: Optional[List[str]] = None


class DirectMessageCreate(BaseSchema):
    """Schema for creating direct messages"""
    content: str = Field(..., min_length=1)
    recipient_id: UUID 
    message_type: str = "text"
    attachments: Optional[List[str]] = None


class OnlineStatusUpdate(BaseSchema):
    """Schema for updating online status"""
    status: str = Field(..., pattern=r'^(online|away|busy|offline)$')
    custom_status: Optional[str] = Field(None, max_length=255)


# Pagination and filtering schemas
class PaginationParams(BaseSchema):
    """Schema for pagination parameters"""
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class ProjectFilters(BaseSchema):
    """Schema for project filtering"""
    status: Optional[ProjectStatus] = None
    priority: Optional[Priority] = None
    project_manager_id: UUID 
    client_id: UUID
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    end_date_from: Optional[date] = None
    end_date_to: Optional[date] = None
    tags: Optional[List[str]] = None
    is_archived: Optional[bool] = None


class TaskFilters(BaseSchema):
    """Schema for task filtering"""
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    project_id: UUID
    assigned_to: Optional[int] = None
    due_date_from: Optional[date] = None
    due_date_to: Optional[date] = None
    is_overdue: Optional[bool] = None
    tags: Optional[List[str]] = None


# Export schemas
class ExportRequest(BaseSchema):
    """Schema for export requests"""
    format: str = Field(..., pattern=r'^(pdf|excel|csv)$')
    entity_type: str = Field(..., pattern=r'^(projects|tasks|timeline|analytics)$')
    filters: Optional[Dict[str, Any]] = None
    date_range: Optional[Dict[str, date]] = None
    include_details: bool = True


class ExportResponse(BaseSchema):
    """Schema for export responses"""
    status: str
    file_path: str
    file_size: str
    generated_at: datetime
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None

