
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

class ProjectTagBase(BaseModel):
    tag_category: str
    tag_value: str
    applied_by: Optional[UUID] = None
    tag_color: Optional[str] = None
    extra: Optional[dict] = None

class ProjectTagCreate(ProjectTagBase):
    pass

class ProjectTagOut(ProjectTagBase):
    id: UUID
    project_id: UUID
    company_id: UUID
    created_at: datetime
    class Config:
        orm_mode = True

class ProjectActivityBase(BaseModel):
    activity_type: str
    subject: str
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    scheduled_date: Optional[datetime] = None
    extra: Optional[dict] = None

class ProjectActivityCreate(ProjectActivityBase):
    pass

class ProjectActivityOut(ProjectActivityBase):
    id: UUID
    project_id: UUID
    company_id: UUID
    created_at: datetime
    class Config:
        orm_mode = True

class ProjectRatingBase(BaseModel):
    rating_type: str
    rating_value: int
    rated_by: Optional[UUID] = None
    comments: Optional[str] = None
    extra: Optional[dict] = None

class ProjectRatingCreate(ProjectRatingBase):
    pass

class ProjectRatingOut(ProjectRatingBase):
    id: UUID
    project_id: UUID
    company_id: UUID
    created_at: datetime
    class Config:
        orm_mode = True

class ProjectTagBase(BaseModel):
    tag_category: str
    tag_value: str
    applied_by: Optional[UUID] = None
    tag_color: Optional[str] = None
    extra: Optional[dict] = None

class ProjectTagCreate(ProjectTagBase):
    pass


class ProjectFinancialDocumentBase(BaseModel):
    document_type: str
    document_number: str
    total_amount: float
    issued_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    extra: Optional[dict] = None

class ProjectFinancialDocumentCreate(ProjectFinancialDocumentBase):
    pass

class ProjectFinancialDocumentOut(ProjectFinancialDocumentBase):
    id: UUID
    project_id: UUID
    company_id: UUID
    created_at: datetime
    class Config:
        orm_mode = True

