from sqlalchemy.orm import Session
from uuid import UUID
from bheem_core.modules.project_management.core.models.project_models import Task
from bheem_core.core.event_bus import EventBus
from bheem_core.modules.project_management.core.schemas.project_task_schemas import TaskCreate, TaskUpdate

class TaskService:
    def __init__(self, db: Session, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    def create_task(self, data: TaskCreate, user_id: UUID):
        task = Task(**data.dict())
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self.event_bus.publish(
            event_type="task.created",
            data={"task_id": str(task.id), "project_id": str(task.project_id)},
            source_module="project_management"
        )
        return task

    def get_task(self, task_id: UUID):
        return self.db.query(Task).get(task_id)

    def update_task(self, task_id: UUID, data: TaskUpdate, user_id: UUID):
        task = self.db.query(Task).get(task_id)
        for k, v in data.dict(exclude_unset=True).items():
            setattr(task, k, v)
        self.db.commit()
        self.event_bus.publish(
            event_type="task.updated",
            data={"task_id": str(task.id), "project_id": str(task.project_id)},
            source_module="project_management"
        )
        return task

    def delete_task(self, task_id: UUID, user_id: UUID):
        task = self.db.query(Task).get(task_id)
        self.db.delete(task)
        self.db.commit()
        self.event_bus.publish(
            event_type="task.deleted",
            data={"task_id": str(task.id), "project_id": str(task.project_id)},
            source_module="project_management"
        )
        return task

    def list_tasks(self, project_id: UUID):
        return self.db.query(Task).filter(Task.project_id == project_id).all()

