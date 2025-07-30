from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, constr

class ProjectPhaseBase(BaseModel):
    name: constr(max_length=255)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    completion_percentage: Optional[int] = Field(0, ge=0, le=100)
    order_sequence: int
    status: Optional[str] = Field("planned", max_length=50)
    dependencies: Optional[List[UUID]] = None
    dependencies: Optional[List[UUID]] = None

class ProjectPhaseCreate(ProjectPhaseBase):
    project_id: UUID

class ProjectPhaseUpdate(BaseModel):
    name: Optional[constr(max_length=255)] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    order_sequence: Optional[int] = None
    status: Optional[str] = Field(None, max_length=50)
    dependencies: Optional[List[UUID]] = None
    dependencies: Optional[List[UUID]] = None

class ProjectPhaseResponse(ProjectPhaseBase):
    id: UUID
    project_id: UUID
    class Config:
        orm_mode = True

