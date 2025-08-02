
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.modules.auth.core.services.permissions_service import require_roles, require_api_permission
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from uuid import UUID
from app.modules.project_management.api.v1.routes.project_phases import router as project_phases_router
from app.modules.auth.core.services.permissions_service import get_current_user, require_api_permission
from app.modules.auth.core.models.auth_models import User
from app.modules.project_management.core.schemas.project_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    TeamMemberAdd,
    TeamMemberResponse,
    ProjectFilters,
    PaginationParams
)
from app.modules.project_management.core.service import ProjectManagementService
from app.modules.project_management.core.services.project_activity_service import ProjectActivityService
from app.modules.project_management.core.schemas.project_activity_schemas import (
    ProjectActivityCreate, ProjectActivityOut,
    ProjectFinancialDocumentCreate, ProjectFinancialDocumentOut,
    ProjectRatingCreate, ProjectRatingOut,
    ProjectTagCreate, ProjectTagOut
)
from app.core.event_bus import EventBus

router = APIRouter(prefix="/project-management/projects", tags=["Project Management - Projects"])
router.include_router(project_phases_router)
event_bus = EventBus()
activity_service = ProjectActivityService

# --- Project Activities ---
@router.post("/{project_id}/activities", response_model=ProjectActivityOut)
def add_project_activity(project_id: UUID, data: ProjectActivityCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = ProjectActivityService(db, event_bus)
    activity = service.add_activity(project_id, data, user.id)
    return ProjectActivityOut.from_orm(activity)

@router.get("/{project_id}/activities", response_model=List[ProjectActivityOut])
def get_project_activities(project_id: UUID, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    activities = service.get_activities(project_id)
    return [ProjectActivityOut.from_orm(a) for a in activities]

# --- Project Financial Documents ---
@router.post("/{project_id}/financial-documents", response_model=ProjectFinancialDocumentOut)
def add_project_financial_document(project_id: UUID, data: ProjectFinancialDocumentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = ProjectActivityService(db, event_bus)
    doc = service.add_financial_document(project_id, data, user.id)
    return ProjectFinancialDocumentOut.from_orm(doc)

@router.get("/{project_id}/financial-documents", response_model=List[ProjectFinancialDocumentOut])
def get_project_financial_documents(project_id: UUID, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    docs = service.get_financial_documents(project_id)
    return [ProjectFinancialDocumentOut.from_orm(d) for d in docs]

# --- Project Ratings ---
@router.post("/{project_id}/ratings", response_model=ProjectRatingOut)
def add_project_rating(project_id: UUID, data: ProjectRatingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = ProjectActivityService(db, event_bus)
    rating = service.add_rating(project_id, data, user.id)
    return ProjectRatingOut.from_orm(rating)

@router.get("/{project_id}/ratings", response_model=List[ProjectRatingOut])
def get_project_ratings(project_id: UUID, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    ratings = service.get_ratings(project_id)
    return [ProjectRatingOut.from_orm(r) for r in ratings]

# --- Project Tags ---
@router.post("/{project_id}/tags", response_model=ProjectTagOut)
def add_project_tag(project_id: UUID, data: ProjectTagCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = ProjectActivityService(db, event_bus)
    tag = service.add_tag(project_id, data, user.id)
    return ProjectTagOut.from_orm(tag)

@router.get("/{project_id}/tags", response_model=List[ProjectTagOut])
def get_project_tags(project_id: UUID, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    tags = service.get_tags(project_id)
    return [ProjectTagOut.from_orm(t) for t in tags]
    service = ProjectActivityService(db, event_bus)
    activity = service.add_activity(project_id, data)
    return ProjectActivityOut.model_validate(activity)

@router.get("/{project_id}/activities", response_model=List[ProjectActivityOut])
def list_project_activities(project_id: UUID, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    activities = service.list_activities(project_id)
    return [ProjectActivityOut.model_validate(a) for a in activities]

# --- Project Ratings ---
@router.post("/{project_id}/ratings", response_model=ProjectRatingOut)
def add_project_rating(project_id: UUID, data: ProjectRatingCreate, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    rating = service.add_rating(project_id, data)
    return ProjectRatingOut.model_validate(rating)

@router.get("/{project_id}/ratings", response_model=List[ProjectRatingOut])
def list_project_ratings(project_id: UUID, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    ratings = service.list_ratings(project_id)
    return [ProjectRatingOut.model_validate(r) for r in ratings]

# --- Project Tags ---
@router.post("/{project_id}/tags", response_model=ProjectTagOut)
def add_project_tag(project_id: UUID, data: ProjectTagCreate, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    tag = service.add_tag(project_id, data)
    return ProjectTagOut.model_validate(tag)

@router.get("/{project_id}/tags", response_model=List[ProjectTagOut])
def list_project_tags(project_id: UUID, db: Session = Depends(get_db)):
    service = ProjectActivityService(db, event_bus)
    tags = service.list_tags(project_id)
    return [ProjectTagOut.model_validate(t) for t in tags]


from fastapi import Query

@router.get("/", response_model=List[ProjectResponse], summary="Get all projects")
async def get_projects(
    company_id: Optional[UUID] = Query(None),
    project_manager_id: Optional[UUID] = Query(None),
    client_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    is_archived: Optional[bool] = Query(None),
    is_template: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    perm=Depends(lambda: require_api_permission("pm.view_project")),
    role=Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER", "USER"]))
):
    """
    Retrieve all projects with optional filtering and pagination via query params only.
    """
    filters = {}
    if company_id:
        filters["company_id"] = company_id
    if project_manager_id:
        filters["project_manager_id"] = project_manager_id
    if client_id:
        filters["client_id"] = client_id
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    if is_archived is not None:
        filters["is_archived"] = is_archived
    if is_template is not None:
        filters["is_template"] = is_template
    service = ProjectManagementService(db)
    projects = await service.get_projects(skip=skip, limit=limit, filters=filters)
    return [ProjectResponse.model_validate(p, from_attributes=True) for p in projects]

@router.post("/", response_model=ProjectResponse, summary="Create new project", status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    perm=Depends(lambda: require_api_permission("project:create"))
):
    """
    Create a new project
    
    Args:
        project_data: Project creation data
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Created project
    """
    event_bus = EventBus()  # In production, use a shared/singleton instance
    service = ProjectManagementService(db, event_bus=event_bus, user=current_user)
    project = await service.create_project(project_data)
    return project


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project by ID")
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    perm=Depends(lambda: require_api_permission("project:read")),
    role=Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER", "USER"]))
):
    """
    Retrieve a specific project by ID
    """
    service = ProjectManagementService(db)
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.put("/{project_id}", response_model=ProjectResponse, summary="Update project")
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    perm=Depends(lambda: require_api_permission("pm.update_project")),
    role=Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER"]))
):
    """
    Update an existing project
    """
    event_bus = EventBus()
    service = ProjectManagementService(db, event_bus=event_bus)
    update_dict = project_data.dict(exclude_unset=True)
    update_dict['updated_by'] = current_user.id
    project = await service.update_project(project_id, update_dict)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.delete("/{project_id}", summary="Delete project", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    perm=Depends(lambda: require_api_permission("project:delete")),
    role=Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER"]))
):
    """
    Delete a project (soft delete)
    """
    event_bus = EventBus()
    service = ProjectManagementService(db, event_bus=event_bus)
    success = await service.delete_project(project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )


@router.get("/{project_id}/tasks", summary="Get project tasks")
async def get_project_tasks(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    assigned_to: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all tasks for a specific project
    
    Args:
        project_id: ID of the project
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter tasks by status
        assigned_to: Filter tasks by assignee
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of project tasks
    """
    service = ProjectManagementService(db)
    
    # Verify project exists
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    filters = {"project_id": project_id}
    if status_filter:
        filters["status"] = status_filter
    if assigned_to:
        filters["assigned_to"] = assigned_to
    
    tasks = service.get_tasks(skip=skip, limit=limit, filters=filters)
    return tasks


@router.get("/{project_id}/budget", summary="Get project budget")
async def get_project_budget(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get budget information for a project
    
    Args:
        project_id: ID of the project
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Project budget details
    """
    service = ProjectManagementService(db)
    
    # Verify project exists
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    budget_info = service.get_budget_utilization(project_id=project_id)
    return budget_info


@router.post("/{project_id}/team-members", response_model=TeamMemberResponse, summary="Add team member to project")
async def add_team_member(
    project_id: int,
    member_data: TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a team member to a project
    
    Args:
        project_id: ID of the project
        member_data: Team member data
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Added team member information
    """
    service = ProjectManagementService(db)
    
    # Verify project exists
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    # Add team member
    member_dict = member_data.dict()
    member_dict['project_id'] = project_id
    member_dict['created_by'] = current_user.id
    
    team_member = service.add_team_member(member_dict)
    return team_member


@router.get("/{project_id}/team-members", response_model=List[TeamMemberResponse], summary="Get project team members")
async def get_project_team_members(
    project_id: int,
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all team members for a project
    
    Args:
        project_id: ID of the project
        is_active: Filter by active status
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of team members
    """
    service = ProjectManagementService(db)
    
    # Verify project exists
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    filters = {"project_id": project_id}
    if is_active is not None:
        filters["is_active"] = is_active
    
    team_members = service.get_team_members(filters)
    return team_members


@router.get("/{project_id}/health", summary="Get project health metrics")
async def get_project_health(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get project health score and metrics
    
    Args:
        project_id: ID of the project
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Project health metrics
    """
    service = ProjectManagementService(db)
    
    # Verify project exists
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    health_metrics = service.get_project_health(project_id)
    return health_metrics
