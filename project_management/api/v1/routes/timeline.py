"""Project Management - Timeline API Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.auth.core.services.permissions_service import get_current_user, require_api_permission, require_roles
from app.modules.auth.core.models.auth_models import User
from app.modules.project_management.core.schemas import ProjectPhaseCreate, ProjectPhaseUpdate, ProjectPhaseResponse
from app.modules.project_management.core.service import ProjectManagementService
from app.core.event_bus import EventBus

router = APIRouter(prefix="/project-management/timeline", tags=["Project Management - Timeline"])

# ---------------------------
# Async-safe permission deps
# ---------------------------

async def permission_view_timeline():
    return await require_api_permission("pm.view_timeline")

async def permission_create_phase():
    return await require_api_permission("pm.create_phase")

async def permission_update_phase():
    return await require_api_permission("pm.update_phase")

async def permission_delete_phase():
    return await require_api_permission("pm.delete_phase")

async def roles_pm_admin():
    return await require_roles("ProjectManager", "Admin", "SuperAdmin")

# ---------------------------
# Service Dependency
# ---------------------------
async def get_service(db: Session = Depends(get_db)):
    event_bus = EventBus()
    return ProjectManagementService(db, event_bus)

# ---------------------------
# Routes
# ---------------------------

@router.get(
    "/projects/{project_id}/timeline",
    summary="Get project timeline",
    dependencies=[Depends(permission_view_timeline)]
)
async def get_project_timeline(
    project_id: int,
    include_dependencies: bool = True,
    include_milestones: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"message": f"Get timeline for project {project_id}", "user": current_user.id}


@router.post(
    "/projects/{project_id}/phases",
    response_model=ProjectPhaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project phase",
    dependencies=[Depends(permission_create_phase), Depends(roles_pm_admin)]
)
async def create_project_phase(
    project_id: int,
    phase_data: ProjectPhaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service),
):
    data = phase_data.dict()
    data["project_id"] = project_id
    phase = await service.create_project_phase(data, creator_id=current_user.id)
    return ProjectPhaseResponse(**phase)


@router.get(
    "/projects/{project_id}/phases",
    response_model=List[ProjectPhaseResponse],
    summary="Get project phases",
    dependencies=[Depends(permission_view_timeline), Depends(roles_pm_admin)]
)
async def get_project_phases(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service),
):
    phases = await service.get_project_phases(project_id)
    return [ProjectPhaseResponse(**p) for p in phases]


@router.put(
    "/phases/{phase_id}",
    response_model=ProjectPhaseResponse,
    summary="Update project phase",
    dependencies=[Depends(permission_update_phase), Depends(roles_pm_admin)]
)
async def update_project_phase(
    phase_id: int,
    phase_data: ProjectPhaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service),
):
    updated = await service.update_project_phase(phase_id, phase_data.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Project phase not found")
    return ProjectPhaseResponse(**updated)


@router.get(
    "/phases/{phase_id}",
    response_model=ProjectPhaseResponse,
    summary="Get project phase by ID",
    dependencies=[Depends(permission_view_timeline), Depends(roles_pm_admin)]
)
async def get_project_phase(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service),
):
    phase = await service.get_project_phase(phase_id)
    if not phase:
        raise HTTPException(status_code=404, detail="Project phase not found")
    return ProjectPhaseResponse(**phase)


@router.delete(
    "/phases/{phase_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project phase",
    dependencies=[Depends(permission_delete_phase), Depends(roles_pm_admin)]
)
async def delete_project_phase(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service),
):
    deleted = await service.delete_project_phase(phase_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project phase not found or already deleted")
    return None
