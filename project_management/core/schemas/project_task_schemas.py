from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    remaining_hours: Optional[float] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    phase_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    is_milestone: Optional[bool] = False
    tags: Optional[dict] = None
    custom_fields: Optional[dict] = None

class TaskCreate(TaskBase):
    title: str
    project_id: UUID

class TaskUpdate(TaskBase):
    pass

class TaskOut(TaskBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    class Config:
        orm_mode = True

