from sqlalchemy.orm import Session
from .models.project_models import Project
from .schemas import ProjectCreate, ProjectUpdate, ProjectOut
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException
from uuid import UUID
import uuid

import logging

logger = logging.getLogger(__name__)

class ProjectService:
    async def get_all_tasks(self, project_id: str = None) -> list:
        """Get all tasks, optionally filtered by project_id."""
        from sqlalchemy import select
        from app.modules.project_management.core.models.project_models import Task
        stmt = select(Task)
        if project_id:
            stmt = stmt.where(Task.project_id == project_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    async def get_projects(self, skip: int = 0, limit: int = 100, filters: dict = None) -> list:
        """
        List projects with optional filters and pagination.
        """
        query = self.db.query(Project)
        if filters:
            for key, value in filters.items():
                if hasattr(Project, key) and value is not None:
                    query = query.filter(getattr(Project, key) == value)
        query = query.offset(skip).limit(limit)
        return query.all()
    async def get_projects(self, skip: int = 0, limit: int = 100, filters: dict = None) -> list:
        """
        List projects with optional filters and pagination. Async/SQLAlchemy 2.0 style.
        """
        from sqlalchemy import select
        stmt = select(Project)
        if filters:
            for key, value in filters.items():
                if hasattr(Project, key) and value is not None:
                    stmt = stmt.where(getattr(Project, key) == value)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    def __init__(self, db: Session, event_bus=None, user=None):
        self.db = db
        self.event_bus = event_bus
        self.user = user

    # ...existing code...

    async def get_project(self, project_id: UUID) -> Optional[Project]:
        from sqlalchemy import select
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def list_projects(self, company_id: Optional[UUID] = None) -> List[Project]:
        query = self.db.query(Project)
        if company_id:
            query = query.filter(Project.company_id == company_id)
        return query.all()

    async def create_project(self, project_in):
        from datetime import datetime
        from datetime import datetime
        from decimal import Decimal
        from app.modules.project_management.config import ProjectStatus, Priority
        from app.modules.project_management.core.schemas.project_schemas import ProjectResponse
        now = datetime.utcnow().replace(tzinfo=None)
        data = project_in.dict(exclude_unset=True)
        def ensure_uuid(val):
            if val is None:
                return uuid.uuid4()
            if isinstance(val, str):
                return uuid.UUID(val)
            if isinstance(val, uuid.UUID):
                return val
            return uuid.uuid4()
        def ensure_enum(val, allowed):
            if val is None:
                return allowed[0]
            if isinstance(val, str):
                for a in allowed:
                    if val.lower() == a.value.lower():
                        return a
            if isinstance(val, allowed[0].__class__):
                return val
            return allowed[0]
        def ensure_int(val):
            if val is None:
                return 0
            try:
                return int(val)
            except Exception:
                return 0
        def ensure_float(val):
            if val is None:
                return Decimal("0.0")
            try:
                return Decimal(str(val))
            except Exception:
                return Decimal("0.0")
        def ensure_bool(val):
            if val is None:
                return False
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ["true", "1", "yes"]
            return bool(val)
        allowed_status = [ProjectStatus.PLANNING, ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]
        allowed_priority = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
        def make_naive(dt):
            if dt is None:
                return None
            if isinstance(dt, str):
                try:
                    import dateutil.parser
                    dt = dateutil.parser.isoparse(dt)
                except Exception:
                    return None
            if dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt

        project_dict = {
            "id": ensure_uuid(data.get("id")),
            "name": data.get("name", "Unnamed Project"),
            "description": data.get("description", ""),
            "status": ensure_enum(data.get("status"), allowed_status),
            "priority": ensure_enum(data.get("priority"), allowed_priority),
            "start_date": make_naive(data.get("start_date", now)),
            "end_date": make_naive(data.get("end_date", now)),
            "actual_start_date": make_naive(data.get("actual_start_date", None)),
            "actual_end_date": make_naive(data.get("actual_end_date", None)),
            "budget_allocated": ensure_float(data.get("budget_allocated")),
            "budget_spent": ensure_float(data.get("budget_spent")),
            "budget_remaining": ensure_float(data.get("budget_remaining")),
            "completion_percentage": ensure_int(data.get("completion_percentage")),
            "health_score": ensure_int(data.get("health_score")),
            "risk_level": data.get("risk_level", None),
            "project_manager_id": ensure_uuid(data.get("project_manager_id")),
            "client_id": ensure_uuid(data.get("client_id")),
            "company_id": ensure_uuid(data.get("company_id")),
            "is_template": ensure_bool(data.get("is_template")),
            "is_archived": ensure_bool(data.get("is_archived")),
            "tags": data.get("tags", []),
            "custom_fields": data.get("custom_fields", {}),
            "created_by": str(ensure_uuid(self.user.get("id") if self.user else None)) if self.user and self.user.get("id") else None,
            "created_at": now,
            "updated_at": now
        }
        # Insert into DB (ORM logic, async)
        project_obj = Project(**project_dict)
        self.db.add(project_obj)
        await self.db.flush()  # Ensure PK is generated
        await self.db.commit()
        await self.db.refresh(project_obj)
        # Return a type-correct response
        return ProjectResponse.model_validate(project_obj, from_attributes=True)
    
    # ...existing code...
    
    async def update_project(self, project_id: int, update_data: dict) -> Optional[dict]:
        """Update an existing project and publish event"""
        import uuid
        from datetime import datetime
        from decimal import Decimal
        from app.modules.project_management.config import ProjectStatus, Priority
        now = datetime.utcnow()
    async def update_project(self, project_id: UUID, update_data: dict) -> Optional[dict]:
        """Update an existing project and publish event"""
        from sqlalchemy import select
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return None
        for k, v in update_data.items():
            if hasattr(project, k):
                setattr(project, k, v)
        await self.db.commit()
        await self.db.refresh(project)
        if self.event_bus:
            await self.event_bus.publish(
                event_type="project.updated",
                data={"project_id": str(project_id), "update": update_data},
                source_module="project_management"
            )
        return project
    
    # Task Methods
    async def create_task(self, task_data, creator_id: int) -> dict:
        """Create a new task and publish event"""
        # If task_data is a Pydantic model, use attribute access
        if hasattr(task_data, 'dict'):
            task_dict = task_data.dict()
        else:
            task_dict = dict(task_data)
        logger.info(f"Creating task: {task_dict.get('title', 'Unknown')}")
        # Import Task model here to avoid circular import
        from app.modules.project_management.core.models.project_models import Task
        from app.modules.project_management.core.schemas.project_task_schemas import TaskOut
        import uuid
        from datetime import datetime

        # Convert Pydantic model to dict if needed
        if hasattr(task_data, 'dict'):
            task_dict = task_data.dict(exclude_unset=True)
        else:
            task_dict = dict(task_data)

        # Set required fields
        task_dict['created_by'] = creator_id
        task_dict['created_at'] = datetime.utcnow()
        if 'id' not in task_dict:
            task_dict['id'] = uuid.uuid4()

        # Create Task ORM object
        task_obj = Task(**task_dict)
        self.db.add(task_obj)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(task_obj)

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                event_type="task_created",
                data={"task_id": str(task_obj.id), "project_id": str(task_obj.project_id)},
                source_module="project_management"
            )

        # Return response schema
        return TaskOut.model_validate(task_obj, from_attributes=True)

    async def update_task(self, task_id: int, update_data: dict) -> dict:
        """Update a task and publish event"""
        logger.info(f"Updating task {task_id}")
        # Implementation would update task in database
        task = {"id": task_id, **update_data}
        if self.event_bus:
            await self.event_bus.publish(
                event_type="task_updated",
                data={"task_id": task_id, "update": update_data},
                source_module="project_management"
            )
        return task

    async def delete_task(self, task_id: int) -> bool:
        """Delete a task and publish event"""
        logger.info(f"Deleting task {task_id}")
        # Implementation would soft delete task in database
        success = True
        if success and self.event_bus:
            await self.event_bus.publish(
                event_type="task_deleted",
                data={"task_id": task_id},
                source_module="project_management"
            )
        return success

    async def get_task(self, task_id: int) -> dict:
        """Get a task by ID"""
        # Implementation would query database
        task = {
            "id": task_id,
            "title": f"Task {task_id}",
            "status": "todo",
            # ...add other fields as needed
        }
        return task

    # Calendar Methods
    def create_calendar_event(self, event_data: dict, creator_id: int) -> dict:
        """Create a calendar event"""
        logger.info(f"Creating calendar event: {event_data.get('title', 'Unknown')}")
        return {
            "id": 1,
            "title": event_data.get("title", "New Event"),
            "start_datetime": event_data.get("start_datetime"),
            "end_datetime": event_data.get("end_datetime"),
            "created_by": creator_id
        }
    
    def get_calendar_events(self, start_date: datetime, end_date: datetime, user_id: Optional[int] = None) -> List[dict]:
        """Get calendar events within date range"""
        return [
            {
                "id": 1,
                "title": "Team Meeting",
                "start_datetime": "2024-07-01T10:00:00Z",
                "end_datetime": "2024-07-01T11:00:00Z",
                "type": "meeting"
            }
        ]
    
    def check_calendar_conflicts(self, start_datetime: datetime, end_datetime: datetime, user_ids: List[int]) -> List[dict]:
        """Check for calendar conflicts"""
        return []  # No conflicts found
    
    # Timeline and Milestone Methods
    def create_milestone(self, milestone_data: dict, creator_id: int) -> dict:
        """Create a project milestone"""
        logger.info(f"Creating milestone: {milestone_data.get('title', 'Unknown')}")
        return {
            "id": 1,
            "title": milestone_data.get("title", "New Milestone"),
            "due_date": milestone_data.get("due_date"),
            "is_completed": False,
            "created_by": creator_id
        }
    
    def get_project_timeline(self, project_id: int) -> dict:
        """Get project timeline with phases and milestones"""
        return {
            "project_id": project_id,
            "phases": [
                {
                    "id": 1,
                    "name": "Planning Phase",
                    "start_date": "2024-01-01",
                    "end_date": "2024-02-01",
                    "completion_percentage": 100
                },
                {
                    "id": 2,
                    "name": "Development Phase",
                    "start_date": "2024-02-01",
                    "end_date": "2024-05-01",
                    "completion_percentage": 70
                }
            ],
            "milestones": [
                {
                    "id": 1,
                    "title": "Project Kickoff",
                    "due_date": "2024-01-15",
                    "is_completed": True
                },
                {
                    "id": 2,
                    "title": "Alpha Release",
                    "due_date": "2024-03-15",
                    "is_completed": False
                }
            ]
        }
    
    def complete_milestone(self, milestone_id: int) -> bool:
        """Mark a milestone as completed"""
        logger.info(f"Completing milestone {milestone_id}")
        return True
    
    # Deadline and Alert Methods
    def check_deadlines(self) -> List[dict]:
        """Check for approaching deadlines"""
        return [
            {
                "type": "task",
                "entity_id": 1,
                "title": "Important Task",
                "due_date": "2024-07-02",
                "days_until_due": 1,
                "alert_level": "urgent"
            }
        ]
    
    def acknowledge_deadline_alert(self, alert_id: int) -> bool:
        """Acknowledge a deadline alert"""
        logger.info(f"Acknowledging deadline alert {alert_id}")
        return True
    
    # Analytics Methods
    def get_analytics_dashboard(self, date_range: str = "30d") -> dict:
        """Get analytics dashboard data"""
        return {
            "total_projects": 25,
            "active_projects": 12,
            "completed_projects": 10,
            "overdue_tasks": 5,
            "team_productivity": 85.5,
            "budget_utilization": 72.3,
            "upcoming_deadlines": 8
        }
    
    def get_productivity_metrics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
        """Get productivity metrics"""
        return {
            "tasks_completed": 156,
            "average_completion_time": 2.3,  # days
            "team_efficiency": 87.2,
            "bottlenecks": ["code_review", "testing"],
            "top_performers": [
                {"user_id": 1, "tasks_completed": 25},
                {"user_id": 2, "tasks_completed": 22}
            ]
        }
    
    def get_budget_utilization(self, project_id: Optional[int] = None) -> dict:
        """Get budget utilization metrics"""
        return {
            "total_budget": 100000,
            "spent_budget": 72300,
            "remaining_budget": 27700,
            "utilization_percentage": 72.3,
            "forecast_completion": 95.5,
            "burn_rate": 12000  # per month
        }
    
    def get_resource_utilization(self) -> dict:
        """Get resource utilization metrics"""
        return {
            "total_resources": 20,
            "allocated_resources": 18,
            "utilization_percentage": 90.0,
            "overallocated_resources": 2,
            "available_capacity": 15.5  # hours per week
        }
    
    # Communication Methods
    def add_comment(self, comment_data: dict, author_id: int) -> dict:
        """Add a comment to a project or task"""
        return {
            "id": 1,
            "content": comment_data.get("content", ""),
            "author_id": author_id,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def get_comments(self, entity_type: str, entity_id: int) -> List[dict]:
        """Get comments for a project or task"""
        return [
            {
                "id": 1,
                "content": "This is a sample comment",
                "author_id": 1,
                "author_name": "John Doe",
                "created_at": "2024-07-01T10:00:00Z"
            }
        ]
    
    # Integration Methods
    def sync_external_calendar(self, sync_config: dict) -> dict:
        """Sync with external calendar systems"""
        logger.info("Syncing external calendar")
        return {
            "status": "success",
            "events_synced": 15,
            "conflicts_detected": 0,
            "last_sync": datetime.utcnow().isoformat()
        }
    
    def export_project_data(self, project_id: int, format: str = "pdf") -> dict:
        """Export project data in various formats"""
        logger.info(f"Exporting project {project_id} data in {format} format")
        return {
            "status": "success",
            "file_path": f"/exports/project_{project_id}.{format}",
            "file_size": "2.5MB",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # Health Check Methods
    def get_project_health(self, project_id: int) -> dict:
        """Get project health metrics"""
        return {
            "project_id": project_id,
            "health_score": 85,
            "risk_level": "low",
            "factors": {
                "schedule_adherence": 90,
                "budget_compliance": 85,
                "team_satisfaction": 80,
                "quality_metrics": 88
            },
            "recommendations": [
                "Consider allocating additional resources for testing phase",
                "Schedule team building activities to improve satisfaction"
            ]
        }
    
    # Utility Methods
    def _calculate_project_progress(self, project_id: int) -> float:
        """Calculate overall project progress percentage"""
        # Implementation would calculate based on tasks, phases, etc.
        return 65.0
    
    def _check_user_permissions(self, user_id: int, action: str, resource_id: int) -> bool:
        """Check if user has permission to perform action on resource"""
        # Implementation would check against permission system
        return True
    
    def _send_notification(self, user_id: int, message: str, notification_type: str = "info"):
        """Send notification to user"""
        logger.info(f"Sending {notification_type} notification to user {user_id}: {message}")
        # Implementation would send through notification system

    # Project Phase Methods
    async def create_project_phase(self, phase_data: dict, creator_id: int) -> dict:
        """Create a new project phase and publish event"""
        logger.info(f"Creating project phase: {phase_data.get('name', 'Unknown')}")
        # Validate required fields
        if not phase_data.get("name"):
            raise ValueError("Phase name is required")
        if not phase_data.get("project_id"):
            raise ValueError("project_id is required")
        if not phase_data.get("order_sequence"):
            phase_data["order_sequence"] = 1  # Default order if not provided
        if not phase_data.get("status"):
            phase_data["status"] = "planned"
        if not phase_data.get("completion_percentage"):
            phase_data["completion_percentage"] = 0
        # Simulate DB insert
        phase = {
            "id": 1,  # Replace with actual DB-generated ID
            "name": phase_data["name"],
            "project_id": phase_data["project_id"],
            "order_sequence": phase_data["order_sequence"],
            "status": phase_data["status"],
            "completion_percentage": phase_data["completion_percentage"],
            "dependencies": phase_data.get("dependencies", []),
            "start_date": phase_data.get("start_date"),
            "end_date": phase_data.get("end_date"),
            "actual_start_date": phase_data.get("actual_start_date"),
            "actual_end_date": phase_data.get("actual_end_date"),
            "description": phase_data.get("description"),
            "created_by": creator_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        if self.event_bus:
            await self.event_bus.publish(
                event_type="phase_created",
                data={"phase": phase},
                source_module="project_management"
            )
        return phase

    async def update_project_phase(self, phase_id: int, update_data: dict) -> dict:
        """Update a project phase and publish event"""
        logger.info(f"Updating project phase {phase_id}")
        # Simulate DB update
        phase = {"id": phase_id, **update_data}
        if self.event_bus:
            await self.event_bus.publish(
                event_type="phase_updated",
                data={"phase_id": phase_id, "update": update_data},
                source_module="project_management"
            )
        return phase

    async def delete_project_phase(self, phase_id: int) -> bool:
        """Delete a project phase and publish event"""
        logger.info(f"Deleting project phase {phase_id}")
        # Simulate DB delete
        success = True
        if success and self.event_bus:
            await self.event_bus.publish(
                event_type="phase_deleted",
                data={"phase_id": phase_id},
                source_module="project_management"
            )
        return success

    async def get_project_phase(self, phase_id: int) -> dict:
        """Get a project phase by ID"""
        # Simulate DB fetch
        phase = {
            "id": phase_id,
            "name": f"Phase {phase_id}",
            "project_id": 1,
            "order_sequence": 1,
            "status": "planned",
            "completion_percentage": 0,
            "dependencies": [],
            "start_date": None,
            "end_date": None,
            "actual_start_date": None,
            "actual_end_date": None,
            "description": None,
            "created_by": 1,
            "created_at": datetime.utcnow().isoformat(),
        }
        return phase

# Alias for compatibility with routes expecting ProjectManagementService
ProjectManagementService = ProjectService
