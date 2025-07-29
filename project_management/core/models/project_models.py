import uuid
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey,
    Enum as SQLEnum, JSON, Index, Numeric, CheckConstraint, Integer  ,text
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression
from app.core.database import Base
from app.core.database import Base, TimestampMixin
from app.shared.models import AuditMixin
from app.shared.models import SoftDeleteMixin
from ...config import ProjectStatus, Priority
from ...config import ProjectStatus, TaskStatus, Priority, CalendarEventTypes, NotificationTypes
from sqlalchemy import and_
from sqlalchemy.orm import foreign
from app.shared.models import Activity, FinancialDocument, Rating, Tag


SCHEMA = "project_management"

class Project(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Project model for managing projects."""

    __tablename__ = "pm_projects"
    __table_args__ = (
        Index(
            "ix_active_projects",
            "id",
            postgresql_where=text("is_active = true AND is_deleted = false")
        ),
        {"schema": SCHEMA}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)

    status = Column(SQLEnum(ProjectStatus, name="project_status"), nullable=False, default=ProjectStatus.PLANNING)
    priority = Column(SQLEnum(Priority, name="project_priority"), nullable=False, default=Priority.MEDIUM)

    start_date = Column(DateTime)
    end_date = Column(DateTime)
    actual_start_date = Column(DateTime)
    actual_end_date = Column(DateTime)

    budget_allocated = Column(Numeric(15, 2))
    budget_spent = Column(Numeric(15, 2), nullable=False, default=0)
    budget_remaining = Column(Numeric(15, 2))

    completion_percentage = Column(
        Integer, CheckConstraint('completion_percentage BETWEEN 0 AND 100'),
        nullable=False, default=0
    )
    health_score = Column(
        Integer, CheckConstraint('health_score BETWEEN 0 AND 100')
    )
    risk_level = Column(String(50))

    project_manager_id = Column(PG_UUID(as_uuid=True), ForeignKey("public.persons.id"))
    client_id = Column(PG_UUID(as_uuid=True), ForeignKey("crm.crm_contacts.id"))
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("public.companies.id"), nullable=False)

    is_template = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    tags = Column(JSON)
    custom_fields = Column(JSON)

    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    phases = relationship("ProjectPhase", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan")
    team_members = relationship("ProjectTeamMember", back_populates="project", cascade="all, delete-orphan")
    dependencies = relationship(
        "ProjectDependency",
        foreign_keys="ProjectDependency.dependent_project_id",
        back_populates="dependent_project"
    )
    dependents = relationship(
        "ProjectDependency",
        foreign_keys="ProjectDependency.dependency_project_id",
        back_populates="dependency_project"
    )
    budget_tracking = relationship("BudgetTracking", back_populates="project", cascade="all, delete-orphan")
    calendar_events = relationship("UniversalCalendar", back_populates="project", cascade="all, delete-orphan")

    # ------------------------------
    # Activity & Rating Utilities
    # ------------------------------

    def get_activities(self):
        from app.shared.models import Activity
        session = object_session(self)
        return session.query(Activity).filter(
            Activity.entity_type == EntityTypes.PROJECT,
            Activity.entity_id == str(self.id),
            Activity.is_active == True
        ).all()

    def add_activity(self, activity_type, subject, description=None, assigned_to=None, scheduled_date=None, **kwargs):
        from app.shared.models import Activity
        session = object_session(self)
        activity = Activity(
            entity_type=EntityTypes.PROJECT,
            entity_id=str(self.id),
            activity_type=activity_type,
            subject=subject,
            description=description,
            assigned_to=assigned_to,
            scheduled_date=scheduled_date,
            company_id=self.company_id,
            **kwargs
        )
        session.add(activity)
        return activity

    def get_financial_documents(self):
        from app.shared.models import FinancialDocument
        session = object_session(self)
        return session.query(FinancialDocument).filter(
            FinancialDocument.party_type == EntityTypes.PROJECT,
            FinancialDocument.party_id == str(self.id),
            FinancialDocument.is_active == True
        ).all()

    def add_financial_document(self, document_type, document_number, total_amount, **kwargs):
        from app.shared.models import FinancialDocument
        session = object_session(self)
        document = FinancialDocument(
            party_type=EntityTypes.PROJECT,
            party_id=str(self.id),
            document_type=document_type,
            document_number=document_number,
            total_amount=total_amount,
            company_id=self.company_id,
            **kwargs
        )
        session.add(document)
        return document

    def get_ratings(self):
        from app.shared.models import Rating
        session = object_session(self)
        return session.query(Rating).filter(
            Rating.entity_type == EntityTypes.PROJECT,
            Rating.entity_id == str(self.id),
            Rating.is_active == True
        ).all()

    def add_rating(self, rating_type, rating_value, rated_by=None, comments=None, **kwargs):
        from app.shared.models import Rating
        session = object_session(self)
        rating = Rating(
            entity_type=EntityTypes.PROJECT,
            entity_id=str(self.id),
            rating_type=rating_type,
            rating_value=rating_value,
            rated_by=rated_by,
            comments=comments,
            company_id=self.company_id,
            **kwargs
        )
        session.add(rating)
        return rating

    def get_tags(self):
        from app.shared.models import Tag
        session = object_session(self)
        return session.query(Tag).filter(
            Tag.entity_type == EntityTypes.PROJECT,
            Tag.entity_id == str(self.id),
            Tag.is_active == True
        ).all()

    def add_tag(self, tag_category, tag_value, applied_by=None, tag_color=None, **kwargs):
        from app.shared.models import Tag
        session = object_session(self)
        tag = Tag(
            entity_type=EntityTypes.PROJECT,
            entity_id=str(self.id),
            tag_category=tag_category,
            tag_value=tag_value,
            applied_by=applied_by,
            tag_color=tag_color,
            company_id=self.company_id,
            **kwargs
        )
        session.add(tag)
        return tag

class Task(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Task model for managing project tasks."""

    __tablename__ = "pm_tasks"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)

    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.TODO)
    priority = Column(SQLEnum(Priority), nullable=False, default=Priority.MEDIUM)

    estimated_hours = Column(Numeric(8, 2))
    actual_hours = Column(Numeric(8, 2), nullable=False, default=0)
    remaining_hours = Column(Numeric(8, 2))

    start_date = Column(DateTime)
    due_date = Column(DateTime)
    completed_date = Column(DateTime)

    completion_percentage = Column(
        Integer,
        CheckConstraint('completion_percentage BETWEEN 0 AND 100'),
        nullable=False,
        default=0
    )

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)
    phase_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_project_phases.id"))
    assigned_to = Column(PG_UUID(as_uuid=True), ForeignKey("public.persons.id"))
    parent_task_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_tasks.id"))

    is_milestone = Column(Boolean, nullable=False, default=False)
    tags = Column(JSON)
    custom_fields = Column(JSON)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    phase = relationship("ProjectPhase", back_populates="tasks")
    time_logs = relationship("TimeLog", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    parent_task = relationship("Task", remote_side="Task.id", back_populates="subtasks")
    subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan")

    # ======================
    # Unified Helper Methods
    # ======================

    def get_activities(self):
        from app.shared.models import Activity
        from sqlalchemy.orm import object_session
        session = object_session(self)
        return session.query(Activity).filter(
            Activity.entity_type == EntityTypes.TASK,
            Activity.entity_id == str(self.id),
            Activity.is_active == True
        ).all()

    def add_activity(self, activity_type, subject, description=None, assigned_to=None, scheduled_date=None, **kwargs):
        from app.shared.models import Activity
        from sqlalchemy.orm import object_session
        session = object_session(self)

        company_id = self.project.company_id if self.project else kwargs.get("company_id")

        activity = Activity(
            entity_type=EntityTypes.TASK,
            entity_id=str(self.id),
            activity_type=activity_type,
            subject=subject,
            description=description,
            assigned_to=assigned_to,
            scheduled_date=scheduled_date,
            company_id=company_id,
            **kwargs
        )
        session.add(activity)
        return activity

    def get_tags(self):
        from app.shared.models import Tag
        from sqlalchemy.orm import object_session
        session = object_session(self)
        return session.query(Tag).filter(
            Tag.entity_type == EntityTypes.TASK,
            Tag.entity_id == str(self.id),
            Tag.is_active == True
        ).all()

    def add_tag(self, tag_category, tag_value, applied_by=None, tag_color=None, **kwargs):
        from app.shared.models import Tag
        from sqlalchemy.orm import object_session
        session = object_session(self)

        company_id = self.project.company_id if self.project else kwargs.get("company_id")

        tag = Tag(
            entity_type=EntityTypes.TASK,
            entity_id=str(self.id),
            tag_category=tag_category,
            tag_value=tag_value,
            applied_by=applied_by,
            tag_color=tag_color,
            company_id=company_id,
            **kwargs
        )
        session.add(tag)
        return tag


class ProjectPhase(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Project phase model for timeline management."""

    __tablename__ = "pm_project_phases"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    start_date = Column(DateTime)
    end_date = Column(DateTime)
    actual_start_date = Column(DateTime)
    actual_end_date = Column(DateTime)

    completion_percentage = Column(
        Integer,
        CheckConstraint('completion_percentage BETWEEN 0 AND 100'),
        nullable=False,
        default=0
    )
    order_sequence = Column(Integer, nullable=False)

    status = Column(String(50), nullable=False, default="planned")  # planned, active, completed, cancelled

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)

    dependencies = Column(JSON)  # List of phase IDs this phase depends on (UUIDs recommended)

    # Relationships
    project = relationship("Project", back_populates="phases")
    tasks = relationship("Task", back_populates="phase", cascade="all, delete-orphan")

    # View-only cross-entity relationships
    activities = relationship(
        "Activity",
        primaryjoin=and_(
            id == foreign(Activity.entity_id),
            Activity.entity_type == 'PROJECT_PHASE'
        ),
        viewonly=True
    )

    financial_documents = relationship(
        "FinancialDocument",
        primaryjoin=and_(
            id == foreign(FinancialDocument.party_id),
            FinancialDocument.party_type == 'PROJECT_PHASE'
        ),
        viewonly=True
    )

    ratings = relationship(
        "Rating",
        primaryjoin=and_(
            id == foreign(Rating.entity_id),
            Rating.entity_type == 'PROJECT_PHASE'
        ),
        viewonly=True
    )

    tags_relation = relationship(
        "Tag",
        primaryjoin=and_(
            id == foreign(Tag.entity_id),
            Tag.entity_type == 'PROJECT_PHASE'
        ),
        viewonly=True
    )



class ProjectMilestone(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Project milestone model."""

    __tablename__ = "pm_milestones"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    due_date = Column(DateTime, nullable=False)
    completion_date = Column(DateTime)

    is_completed = Column(Boolean, nullable=False, default=False)
    is_critical = Column(Boolean, nullable=False, default=False)

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)
    phase_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_project_phases.id"))
    responsible_employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"))
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="milestones")
    calendar_events = relationship("UniversalCalendar", back_populates="milestone", cascade="all, delete-orphan")

    # Unified view-only relationships
    activities = relationship(
        "Activity",
        primaryjoin=and_(
            id == foreign(Activity.entity_id),
            Activity.entity_type == 'PROJECT_MILESTONE'
        ),
        viewonly=True
    )

    financial_documents = relationship(
        "FinancialDocument",
        primaryjoin=and_(
            id == foreign(FinancialDocument.party_id),
            FinancialDocument.party_type == 'PROJECT_MILESTONE'
        ),
        viewonly=True
    )

    ratings = relationship(
        "Rating",
        primaryjoin=and_(
            id == foreign(Rating.entity_id),
            Rating.entity_type == 'PROJECT_MILESTONE'
        ),
        viewonly=True
    )

    tags_relation = relationship(
        "Tag",
        primaryjoin=and_(
            id == foreign(Tag.entity_id),
            Tag.entity_type == 'PROJECT_MILESTONE'
        ),
        viewonly=True
    )


class ProjectTeamMember(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Project team member assignments."""

    __tablename__ = "pm_team_members"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"), nullable=False)

    role = Column(String(100), nullable=False)  # project_manager, developer, etc.
    permissions = Column(JSON)  # List of specific permissions

    allocation_percentage = Column(
        Integer,
        CheckConstraint('allocation_percentage BETWEEN 0 AND 100'),
        nullable=False,
        default=100
    )
    hourly_rate = Column(Numeric(10, 2))

    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime)

    is_active = Column(Boolean, nullable=False, default=True)

    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    # Relationship
    project = relationship("Project", back_populates="team_members")

    # Unified relationships (view-only)
    activities = relationship(
        "Activity",
        primaryjoin=and_(
            id == foreign(Activity.entity_id),
            Activity.entity_type == 'PROJECT_TEAM_MEMBER'
        ),
        viewonly=True
    )

    financial_documents = relationship(
        "FinancialDocument",
        primaryjoin=and_(
            id == foreign(FinancialDocument.party_id),
            FinancialDocument.party_type == 'PROJECT_TEAM_MEMBER'
        ),
        viewonly=True
    )

    ratings = relationship(
        "Rating",
        primaryjoin=and_(
            id == foreign(Rating.entity_id),
            Rating.entity_type == 'PROJECT_TEAM_MEMBER'
        ),
        viewonly=True
    )

    tags_relation = relationship(
        "Tag",
        primaryjoin=and_(
            id == foreign(Tag.entity_id),
            Tag.entity_type == 'PROJECT_TEAM_MEMBER'
        ),
        viewonly=True
    )



class UniversalCalendar(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Universal calendar for project management events."""

    __tablename__ = "pm_calendar_events"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    event_type = Column(SQLEnum(CalendarEventTypes), nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    location = Column(String(255))

    is_recurring = Column(Boolean, nullable=False, default=False)
    recurrence_rule = Column(String(255))  # RRULE format

    status = Column(String(50), nullable=False, default="confirmed")  # confirmed, tentative, cancelled
    visibility = Column(String(50), nullable=False, default="public")  # public, private, confidential
    priority = Column(SQLEnum(Priority), nullable=False, default=Priority.MEDIUM)

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"))
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_tasks.id"))
    milestone_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_milestones.id"))
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    attendee_ids = Column(JSON)  # List of user UUIDs
    attendee_responses = Column(JSON)  # {user_id: "accepted/declined/tentative"}
    reminder_minutes = Column(JSON)  # [15, 60, 1440]

    external_event_id = Column(String(255))  # ID from external calendar system
    external_calendar_source = Column(String(100))  # google, outlook, etc.

    color = Column(String(7))  # Hex color code
    url = Column(String(500))  # Meeting URL for video calls

    # Relationships
    project = relationship("Project", back_populates="calendar_events")
    milestone = relationship("ProjectMilestone", back_populates="calendar_events")


class TimeLog(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Time tracking for tasks and projects."""

    __tablename__ = "pm_time_logs"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_hours = Column(Numeric(8, 2), nullable=False)

    description = Column(Text)
    activity_type = Column(String(100))  # development, testing, meeting, etc.

    is_billable = Column(Boolean, nullable=False, default=True)
    hourly_rate = Column(Numeric(10, 2))
    billable_amount = Column(Numeric(10, 2))

    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_tasks.id"), nullable=False)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)

    is_approved = Column(Boolean, nullable=False, default=False)
    approved_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"))
    approved_at = Column(DateTime)

    # Relationship
    task = relationship("Task", back_populates="time_logs")


class Comment(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Comments for projects, tasks, and milestones."""

    __tablename__ = "pm_comments"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    content = Column(Text, nullable=False)

    comment_type = Column(String(50), nullable=False)  # project, task, milestone

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"))
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_tasks.id"))
    milestone_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_milestones.id"))

    parent_comment_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_comments.id"))
    author_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    mentioned_users = Column(JSON)  # List of user UUIDs mentioned
    attachments = Column(JSON)  # List of file paths/URLs

    is_edited = Column(Boolean, nullable=False, default=False)

    # Relationships
    task = relationship("Task", back_populates="comments")
    parent_comment = relationship("Comment", remote_side="Comment.id", back_populates="replies")
    replies = relationship("Comment", back_populates="parent_comment", cascade="all, delete-orphan")


class Notification(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Notification system for project management."""

    __tablename__ = "pm_notifications"
    __table_args__ = {'schema': 'public'}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    recipient_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)
    sender_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"))

    notification_type = Column(SQLEnum(NotificationTypes, name="notification_types_enum"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    related_entity_type = Column(String(50))  # project, task, milestone, etc.
    related_entity_id = Column(PG_UUID(as_uuid=True))

    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime)

    email_sent = Column(Boolean, nullable=False, default=False)
    sms_sent = Column(Boolean, nullable=False, default=False)
    push_sent = Column(Boolean, nullable=False, default=False)

    priority = Column(SQLEnum(Priority, name="priority_enum"), nullable=False, default=Priority.MEDIUM)

    expires_at = Column(DateTime)

    action_url = Column(String(500))
    meta = Column(JSON)



class DeadlineAlert(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Deadline alerts and reminders for project entities."""

    __tablename__ = "pm_deadline_alerts"
    __table_args__ = {'schema': 'public'}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    entity_type = Column(String(50), nullable=False)  # project, task, milestone
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False)  # UUID of the entity

    alert_type = Column(String(50), nullable=False)  # overdue, due_soon, at_risk
    alert_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    days_difference = Column(Integer, nullable=False)

    is_acknowledged = Column(Boolean, nullable=False, default=False)
    acknowledged_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"))
    acknowledged_at = Column(DateTime)


class ProjectDependency(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Project dependencies tracking."""

    __tablename__ = "pm_project_dependencies"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    dependent_project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)
    dependency_project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)

    dependency_type = Column(String(50), nullable=False)  # finish_to_start, start_to_start, etc.
    is_active = Column(Boolean, nullable=False, default=True)

    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    # Relationships
    dependent_project = relationship(
        "Project",
        foreign_keys=[dependent_project_id],
        back_populates="dependencies"
    )

    dependency_project = relationship(
        "Project",
        foreign_keys=[dependency_project_id],
        back_populates="dependents"
    )




class ResourceAllocation(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Resource allocation tracking for projects and tasks."""

    __tablename__ = "pm_resource_allocations"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    resource_type = Column(String(50), nullable=False)  # human, equipment, facility
    resource_id = Column(PG_UUID(as_uuid=True), nullable=False)  # employee_id, equipment_id, etc.

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_tasks.id"))

    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)

    allocation_percentage = Column(
        Integer,
        CheckConstraint('allocation_percentage BETWEEN 0 AND 100'),
        nullable=False,
        default=100
    )

    cost_per_hour = Column(Numeric(10, 2))
    total_cost = Column(Numeric(15, 2))

    status = Column(String(50), nullable=False, default="allocated")  # allocated, in_use, completed

    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)


class BudgetTracking(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Budget tracking for projects."""

    __tablename__ = "pm_budget_tracking"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"), nullable=False)

    category = Column(String(100), nullable=False)  # labor, materials, equipment, overhead
    subcategory = Column(String(100))

    budgeted_amount = Column(Numeric(15, 2), nullable=False)
    actual_amount = Column(Numeric(15, 2), nullable=False, default=0)
    committed_amount = Column(Numeric(15, 2), nullable=False, default=0)

    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    description = Column(Text)

    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    # Relationship
    project = relationship("Project", back_populates="budget_tracking")



class ChatChannel(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Chat channels for project communication."""

    __tablename__ = "pm_chat_channels"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    channel_type = Column(String(50), nullable=False)  # project, team, direct, public
    is_private = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_projects.id"))
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)

    # Relationships
    members = relationship("ChatMember", back_populates="channel", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="channel", cascade="all, delete-orphan")



class ChatMember(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Chat channel membership."""

    __tablename__ = "pm_chat_members"
    __table_args__ = {'schema': 'public'}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    channel_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_chat_channels.id"), nullable=False)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"), nullable=False)

    role = Column(String(50), nullable=False, default="member")  # admin, moderator, member

    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_read_at = Column(DateTime)

    is_active = Column(Boolean, nullable=False, default=True)

    # Relationship
    channel = relationship("ChatChannel", back_populates="members")



class ChatMessage(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Chat messages within channels, supporting threads and reactions."""

    __tablename__ = "pm_chat_messages"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=False, default="text")  # text, file, image, system

    channel_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_chat_channels.id"), nullable=False)
    sender_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"), nullable=False)

    parent_message_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_chat_messages.id"))

    thread_count = Column(Integer, nullable=False, default=0)

    mentioned_users = Column(JSON)
    attachments = Column(JSON)

    is_edited = Column(Boolean, nullable=False, default=False)
    is_pinned = Column(Boolean, nullable=False, default=False)

    # Relationships
    channel = relationship("ChatChannel", back_populates="messages")

    reactions = relationship(
        "MessageReaction",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    parent_message = relationship(
        "ChatMessage",
        remote_side="ChatMessage.id",
        back_populates="replies"
    )

    replies = relationship(
        "ChatMessage",
        back_populates="parent_message",
        cascade="all, delete-orphan"
    )

class MessageReaction(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Message reactions (emojis) for chat messages."""

    __tablename__ = "pm_message_reactions"
    __table_args__ = ({"schema": "project_management"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    message_id = Column(PG_UUID(as_uuid=True), ForeignKey("project_management.pm_chat_messages.id"), nullable=False)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"), nullable=False)

    emoji = Column(String(50), nullable=False)

    # Relationship
    message = relationship("ChatMessage", back_populates="reactions")



class DirectMessage(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Direct messages exchanged between employees."""

    __tablename__ = "pm_direct_messages"
    __table_args__ = {'schema': 'public'}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=False, default="text")

    sender_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"), nullable=False)
    recipient_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"), nullable=False)

    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime)

    attachments = Column(JSON)


class OnlineStatus(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Tracks employee online status for chat and collaboration tools."""

    __tablename__ = "pm_online_status"
    __table_args__ = ({"schema": "public"},)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("hr.employees.id"), nullable=False, unique=True)

    status = Column(String(50), nullable=False, default="offline")  # online, away, busy, offline
    custom_status = Column(String(255))

    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow)