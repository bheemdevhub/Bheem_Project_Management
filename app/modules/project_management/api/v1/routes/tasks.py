"""Project Management - Tasks API Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.auth.core.services.permissions_service import get_current_user, require_api_permission
from app.modules.auth.core.models.auth_models import User

from app.modules.project_management.core.services.project_task_service import TaskService
from app.modules.project_management.core.schemas import TaskCreate, TaskUpdate, TaskOut, TaskAssignment, TaskResponse
from app.modules.project_management.core.service import ProjectManagementService

from app.core.event_bus import EventBus
from app.modules.auth.core.services.permissions_service import require_roles, require_api_permission

def get_service(db=Depends(get_db)):
    return ProjectManagementService(db, event_bus=EventBus())


router = APIRouter(prefix="/project-management/tasks", tags=["Project Management - Tasks"])

# ---------------------------
# Service Dependencies
# ---------------------------

# ---------------------------
# Routes (with permission dependencies in decorator)
# ---------------------------


# --- CREATE TASK ---
@router.post(
    "/",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    dependencies=[Depends(lambda: require_api_permission("project.task.create")), Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER", "USER"]))]
)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service)
):
    task = await service.create_task(data, current_user["user_id"])
    # Event: task.created is triggered in service
    return task

# --- GET ALL TASKS ---
@router.get(
    "/",
    response_model=List[TaskOut],
    summary="Get all tasks",
    dependencies=[Depends(lambda: require_api_permission("project.task.read")), Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER", "USER"]))]
)
async def get_tasks(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service)
):
    tasks = await service.get_all_tasks(project_id=project_id)
    return tasks

# --- GET TASK BY ID ---
@router.get(
    "/{task_id}",
    response_model=TaskOut,
    summary="Get a task by ID",
    dependencies=[Depends(lambda: require_api_permission("project.task.read")), Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER", "USER"]))]
)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service)
):
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

# --- UPDATE TASK ---
@router.put(
    "/{task_id}",
    response_model=TaskOut,
    summary="Update a task",
    dependencies=[Depends(lambda: require_api_permission("project.task.update")), Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER"]))]
)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service)
):
    task = await service.update_task(task_id, data, user_id=current_user["user_id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

# --- DELETE TASK ---
@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    dependencies=[Depends(lambda: require_api_permission("project.task.delete")), Depends(lambda: require_roles(["ADMIN", "PROJECT_MANAGER"]))]
)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    service: ProjectManagementService = Depends(get_service)
):
    deleted = await service.delete_task(task_id, user_id=current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return None
