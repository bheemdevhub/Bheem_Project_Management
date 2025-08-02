from sqlalchemy.orm import Session
from uuid import UUID
from app.modules.project_management.core.models.project_models import Project
from app.core.event_bus import EventBus

class ProjectActivityService:
    def __init__(self, db: Session, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    def add_activity(self, project_id: UUID, data):
        project = self.db.query(Project).get(project_id)
        activity = project.add_activity(**data.dict())
        self.db.commit()
        self.event_bus.publish(
            event_type="project.activity_added",
            data={"project_id": str(project_id), "activity_type": data.activity_type},
            source_module="project_management"
        )
        return activity

    def get_activities(self, project_id: UUID):
        project = self.db.query(Project).get(project_id)
        return project.get_activities()

    def add_financial_document(self, project_id: UUID, data):
        project = self.db.query(Project).get(project_id)
        doc = project.add_financial_document(**data.dict())
        self.db.commit()
        self.event_bus.publish(
            event_type="project.financial_document_added",
            data={"project_id": str(project_id), "document_type": data.document_type},
            source_module="project_management"
        )
        return doc

    def get_financial_documents(self, project_id: UUID):
        project = self.db.query(Project).get(project_id)
        return project.get_financial_documents()

    def add_rating(self, project_id: UUID, data):
        project = self.db.query(Project).get(project_id)
        rating = project.add_rating(**data.dict())
        self.db.commit()
        self.event_bus.publish(
            event_type="project.rating_added",
            data={"project_id": str(project_id), "rating_type": data.rating_type},
            source_module="project_management"
        )
        return rating

    def get_ratings(self, project_id: UUID):
        project = self.db.query(Project).get(project_id)
        return project.get_ratings()

    def add_tag(self, project_id: UUID, data):
        project = self.db.query(Project).get(project_id)
        tag = project.add_tag(**data.dict())
        self.db.commit()
        self.event_bus.publish(
            event_type="project.tag_added",
            data={"project_id": str(project_id), "tag_category": data.tag_category},
            source_module="project_management"
        )
        return tag

    def get_tags(self, project_id: UUID):
        project = self.db.query(Project).get(project_id)
        return project.get_tags()
