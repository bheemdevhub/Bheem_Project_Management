from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum

class ProjectStatus(str, Enum):
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANNING
    priority: str = "MEDIUM"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    budget_allocated: Optional[float] = None
    budget_spent: Optional[float] = 0
    budget_remaining: Optional[float] = None                                           
    completion_percentage: Optional[int] = 0
    health_score: Optional[int] = None
    risk_level: Optional[str] = None
    project_manager_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    is_template: bool = False
    is_archived: bool = False
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    id: UUID
    project_manager_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    completion_percentage: Optional[int] = None
    health_score: Optional[int] = None
    risk_level: Optional[str] = None
    budget_spent: Optional[float] = None
    budget_remaining: Optional[float] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    is_template: Optional[bool] = None
    is_archived: Optional[bool] = None
    created_by: Optional[UUID] = None
    updated_at: Optional[datetime] = None
    class Config:
        orm_mode = True

