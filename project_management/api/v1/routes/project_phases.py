from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from uuid import UUID
from bheem_core.modules.project_management.core.schemas.project_phase_schemas import (
    ProjectPhaseCreate, ProjectPhaseUpdate, ProjectPhaseResponse
)
from bheem_core.modules.project_management.core.services.project_phase_service import ProjectPhaseService
from bheem_core.core.database import get_db
from bheem_core.core.event_bus import EventBus
from bheem_core.modules.auth.core.services.permissions_service import (
    require_roles, require_api_permission, get_current_user
)

router = APIRouter(prefix="/project-phases", tags=["Project Phases"])

def get_service(db=Depends(get_db)):
    return ProjectPhaseService(db, event_bus=EventBus())

@router.post("/", response_model=ProjectPhaseResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(lambda: require_api_permission("pm.phase.create")), Depends(require_roles(["ADMIN", "PROJECT_MANAGER"]))])
async def create_phase(data: ProjectPhaseCreate, service: ProjectPhaseService = Depends(get_service)):
    phase = await service.create_phase(data)
    return phase

@router.get("/{phase_id}", response_model=ProjectPhaseResponse,
    dependencies=[Depends(lambda: require_api_permission("pm.phase.read")), Depends(require_roles(["ADMIN", "PROJECT_MANAGER", "USER"]))])
async def get_phase(phase_id: UUID, service: ProjectPhaseService = Depends(get_service)):
    phase = await service.get_phase(phase_id)
    if not phase:
        raise HTTPException(status_code=404, detail="Project phase not found")
    return phase

@router.get("/", response_model=List[ProjectPhaseResponse],
    dependencies=[Depends(lambda: require_api_permission("pm.phase.read")), Depends(require_roles(["ADMIN", "PROJECT_MANAGER", "USER"]))])
async def list_phases(
    project_id: UUID = Query(..., description="Project UUID to filter phases"),
    service: ProjectPhaseService = Depends(get_service)
):
    phases = await service.list_phases(project_id)
    return phases

@router.put("/{phase_id}", response_model=ProjectPhaseResponse,
    dependencies=[Depends(lambda: require_api_permission("pm.phase.update")), Depends(require_roles(["ADMIN", "PROJECT_MANAGER"]))])
async def update_phase(phase_id: UUID, data: ProjectPhaseUpdate, service: ProjectPhaseService = Depends(get_service)):
    phase = await service.update_phase(phase_id, data)
    if not phase:
        raise HTTPException(status_code=404, detail="Project phase not found")
    return phase

@router.delete("/{phase_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(lambda: require_api_permission("pm.phase.delete")), Depends(require_roles(["ADMIN", "PROJECT_MANAGER"]))])
async def delete_phase(phase_id: UUID, service: ProjectPhaseService = Depends(get_service)):
    deleted = await service.delete_phase(phase_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project phase not found")
    return None

