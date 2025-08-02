# app/modules/project_management/module.py
"""Main Project Management Module Class"""
from typing import List
import logging
from ...core.base_module import BaseERPModule
from .api.v1.routes import projects, tasks, calendar, timeline, analytics, chat_routes
from .config import ProjectEventTypes, ChatPermissions

logger = logging.getLogger(__name__)

class ProjectManagementModule(BaseERPModule):
    """Project Management Module"""
    
    def __init__(self):
        super().__init__()
        self._event_handlers = None

    def _setup_routes(self) -> None:
        """Setup Project Management module routes"""
        self._router.include_router(projects.router, prefix="/projects", tags=["Projects"])
        try:
            from .api.v1.routes import project_phases
            self._router.include_router(project_phases.router, prefix="/project-phases", tags=["Project Phases"])
        except ImportError:
            pass
    
    @property
    def name(self) -> str:
        return "project_management"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def permissions(self) -> List[str]:
        return [
            # Project permissions
            "pm.create_project",
            "pm.update_project",
            "pm.view_project",
            "pm.delete_project",
            "pm.archive_project",
            
            # Task permissions
            "pm.create_task",
            "pm.update_task",
            "pm.view_task",
            "pm.delete_task",
            "pm.assign_task",
            "pm.complete_task",
            
            # Team permissions
            "pm.add_team_member",
            "pm.remove_team_member",
            "pm.view_team",
            "pm.manage_roles",
            
            # Timeline permissions
            "pm.create_milestone",
            "pm.update_milestone",
            "pm.view_timeline",
            "pm.create_phase",
            "pm.update_phase",
            
            # Calendar permissions
            "pm.create_event",
            "pm.update_event",
            "pm.view_calendar",
            "pm.manage_meetings",
            
            # Resource permissions
            "pm.allocate_resources",
            "pm.view_utilization",
            "pm.manage_budget",
            
            # Time tracking permissions
            "pm.log_time",
            "pm.approve_time",
            "pm.view_timesheets",
            
            # Analytics permissions
            "pm.view_analytics",
            "pm.view_reports",
            "pm.export_data",
            
            # Admin permissions
            "pm.admin_settings",
            "pm.manage_integrations",
            
            # Chat permissions
            "pm.chat.create_channel",
            "pm.chat.view_channel", 
            "pm.chat.edit_channel",
            "pm.chat.delete_channel",
            "pm.chat.archive_channel",
            "pm.chat.add_member",
            "pm.chat.remove_member",
            "pm.chat.manage_roles",
            "pm.chat.view_members",
            "pm.chat.send_message",
            "pm.chat.edit_message",
            "pm.chat.delete_message",
            "pm.chat.view_messages",
            "pm.chat.pin_message",
            "pm.chat.add_reaction",
            "pm.chat.remove_reaction",
            "pm.chat.view_reactions",
            "pm.chat.send_direct_message",
            "pm.chat.view_direct_messages",
            "pm.chat.moderate",
            "pm.chat.view_analytics"
        ]

    def _setup_routes(self) -> None:
        """Setup Project Management module routes"""
        self._router.include_router(projects.router, prefix="/projects", tags=["Projects"])
        self._router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
        self._router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
        self._router.include_router(timeline.router, prefix="/timeline", tags=["Timeline"])
        self._router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
        self._router.include_router(chat_routes.router, prefix="/chat", tags=["Chat & Collaboration"])
        
        # Add module health endpoint (inherited from base)
        super()._setup_routes()

    async def _subscribe_to_events(self) -> None:
        """Subscribe to events from other modules"""
        if self._event_bus:
            # Listen for HR events
            await self._event_bus.subscribe("hr.employee_created", self._handle_employee_created)
            await self._event_bus.subscribe("hr.employee_terminated", self._handle_employee_terminated)
            
            # Listen for CRM events
            await self._event_bus.subscribe("crm.opportunity_won", self._handle_opportunity_won)
            await self._event_bus.subscribe("crm.contact_created", self._handle_contact_created)
            
            # Listen for internal project events
            await self._event_bus.subscribe(ProjectEventTypes.PROJECT_CREATED, self._handle_project_created)
            await self._event_bus.subscribe(ProjectEventTypes.PROJECT_STATUS_CHANGED, self._handle_project_status_changed)
            await self._event_bus.subscribe(ProjectEventTypes.TASK_ASSIGNED, self._handle_task_assigned)
            await self._event_bus.subscribe(ProjectEventTypes.TASK_COMPLETED, self._handle_task_completed)
            await self._event_bus.subscribe(ProjectEventTypes.MILESTONE_COMPLETED, self._handle_milestone_completed)
            await self._event_bus.subscribe(ProjectEventTypes.DEADLINE_APPROACHING, self._handle_deadline_approaching)

    # Event handlers
    async def _handle_employee_created(self, event):
        """Handle employee creation - update team member pool"""
        self._logger.info(f"Employee created: {event.data.get('employee_id')}")
        
    async def _handle_employee_terminated(self, event):
        """Handle employee termination - reassign tasks"""
        self._logger.info(f"Employee terminated: {event.data.get('employee_id')}")
        
    async def _handle_opportunity_won(self, event):
        """Handle won opportunity - auto-create project"""
        self._logger.info(f"Opportunity won: {event.data.get('opportunity_id')}")
        
    async def _handle_contact_created(self, event):
        """Handle contact creation - potential project stakeholder"""
        self._logger.info(f"Contact created: {event.data.get('contact_id')}")
        
    async def _handle_project_created(self, event):
        """Handle project creation - setup project workflow"""
        self._logger.info(f"Project created: {event.data.get('project_id')}")
        
    async def _handle_project_status_changed(self, event):
        """Handle project status changes"""
        self._logger.info(f"Project status changed: {event.data.get('project_id')}")
        
    async def _handle_task_assigned(self, event):
        """Handle task assignments"""
        self._logger.info(f"Task assigned: {event.data.get('task_id')}")
        
    async def _handle_task_completed(self, event):
        """Handle task completion"""
        self._logger.info(f"Task completed: {event.data.get('task_id')}")
        
    async def _handle_milestone_completed(self, event):
        """Handle milestone completion"""
        self._logger.info(f"Milestone completed: {event.data.get('milestone_id')}")
        
    async def _handle_deadline_approaching(self, event):
        """Handle approaching deadlines"""
        self._logger.info(f"Deadline approaching: {event.data.get('entity_id')}")

    async def initialize(self) -> None:
        """Initialize Project Management module"""
        await super().initialize()
        await self._subscribe_to_events()
        self._logger.info("Project Management Module initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown Project Management module"""
        self._logger.info("Shutting down Project Management Module")
        await super().shutdown()

    def initialize(self) -> bool:
        """Initialize the Project Management module"""
        try:
            logger.info(f"Initializing {self.name} module v{self.version}")
            
            # Register event subscriptions
            self._register_event_subscriptions()
            
            # Initialize services and configurations
            self._initialize_services()
            
            # Set up background tasks
            self._setup_background_tasks()
            
            logger.info(f"{self.name} module initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name} module: {str(e)}")
            return False

    def _register_event_subscriptions(self):
        """Register event subscriptions for project management workflows"""
        
        # Project lifecycle events
        self.event_bus.subscribe(ProjectEventTypes.PROJECT_CREATED, self.handle_project_created)
        self.event_bus.subscribe(ProjectEventTypes.PROJECT_STATUS_CHANGED, self.handle_project_status_changed)
        self.event_bus.subscribe(ProjectEventTypes.PROJECT_BUDGET_EXCEEDED, self.handle_budget_exceeded)
        
        # Task management events
        self.event_bus.subscribe(ProjectEventTypes.TASK_ASSIGNED, self.handle_task_assigned)
        self.event_bus.subscribe(ProjectEventTypes.TASK_COMPLETED, self.handle_task_completed)
        self.event_bus.subscribe(ProjectEventTypes.TASK_OVERDUE, self.handle_task_overdue)
        
        # Milestone and timeline events
        self.event_bus.subscribe(ProjectEventTypes.MILESTONE_COMPLETED, self.handle_milestone_completed)
        self.event_bus.subscribe(ProjectEventTypes.DEADLINE_APPROACHING, self.handle_deadline_approaching)
        self.event_bus.subscribe(ProjectEventTypes.PHASE_COMPLETED, self.handle_phase_completed)
        
        # Calendar and scheduling events
        self.event_bus.subscribe(ProjectEventTypes.CALENDAR_EVENT_CREATED, self.handle_calendar_event_created)
        self.event_bus.subscribe(ProjectEventTypes.CALENDAR_CONFLICT_DETECTED, self.handle_calendar_conflict)
        self.event_bus.subscribe(ProjectEventTypes.MEETING_REMINDER, self.handle_meeting_reminder)
        
        # Resource management events
        self.event_bus.subscribe(ProjectEventTypes.RESOURCE_ALLOCATED, self.handle_resource_allocated)
        self.event_bus.subscribe(ProjectEventTypes.RESOURCE_OVERALLOCATED, self.handle_resource_overallocation)
        self.event_bus.subscribe(ProjectEventTypes.TEAM_MEMBER_ADDED, self.handle_team_member_added)
        
        # Communication events
        self.event_bus.subscribe(ProjectEventTypes.PROJECT_MESSAGE_SENT, self.handle_project_message)
        self.event_bus.subscribe(ProjectEventTypes.COMMENT_ADDED, self.handle_comment_added)
        
        # Inter-module event subscriptions
        # HR module events
        self.event_bus.subscribe("hr.employee.status_changed", self.handle_employee_status_change)
        self.event_bus.subscribe("hr.employee.skill_updated", self.handle_employee_skill_update)
        
        # CRM module events
        self.event_bus.subscribe("crm.opportunity.won", self.handle_opportunity_won)
        self.event_bus.subscribe("crm.contact.created", self.handle_contact_created)
        
        # Accounting module events
        self.event_bus.subscribe("accounting.budget.approved", self.handle_budget_approved)
        self.event_bus.subscribe("accounting.invoice.paid", self.handle_invoice_paid)

    def _initialize_services(self):
        """Initialize module services and configurations"""
        # This would initialize database connections, external APIs, etc.
        pass

    def _setup_background_tasks(self):
        """Set up background tasks for project management"""
        # This would set up Celery tasks for deadline monitoring, notifications, etc.
        pass

    # Event Handlers
    async def handle_project_created(self, event_data: dict):
        """Handle project creation event"""
        logger.info(f"Handling project created event: {event_data}")
        
        # Create default project structure
        # Set up initial calendar events
        # Send notifications to stakeholders
        # Initialize project analytics tracking
        pass

    async def handle_project_status_changed(self, event_data: dict):
        """Handle project status change event"""
        logger.info(f"Handling project status change: {event_data}")
        
        # Update dependent projects
        # Notify team members
        # Update resource allocations
        # Generate status reports
        pass

    async def handle_budget_exceeded(self, event_data: dict):
        """Handle budget exceeded event"""
        logger.warning(f"Budget exceeded for project: {event_data}")
        
        # Send alerts to project managers
        # Create budget variance reports
        # Suggest corrective actions
        pass

    async def handle_task_assigned(self, event_data: dict):
        """Handle task assignment event"""
        logger.info(f"Handling task assignment: {event_data}")
        
        # Send notification to assignee
        # Update resource utilization
        # Create calendar reminders
        # Check for conflicts
        pass

    async def handle_task_completed(self, event_data: dict):
        """Handle task completion event"""
        logger.info(f"Handling task completion: {event_data}")
        
        # Update project progress
        # Check milestone completion
        # Update team productivity metrics
        # Trigger dependent tasks
        pass

    async def handle_task_overdue(self, event_data: dict):
        """Handle overdue task event"""
        logger.warning(f"Task overdue: {event_data}")
        
        # Send escalation notifications
        # Update project risk assessment
        # Suggest resource reallocation
        pass

    async def handle_milestone_completed(self, event_data: dict):
        """Handle milestone completion event"""
        logger.info(f"Milestone completed: {event_data}")
        
        # Send congratulations to team
        # Update project timeline
        # Trigger next phase activities
        # Generate milestone reports
        pass

    async def handle_deadline_approaching(self, event_data: dict):
        """Handle approaching deadline event"""
        logger.info(f"Deadline approaching: {event_data}")
        
        # Send reminder notifications
        # Check progress status
        # Suggest acceleration strategies
        pass

    async def handle_phase_completed(self, event_data: dict):
        """Handle project phase completion"""
        logger.info(f"Phase completed: {event_data}")
        
        # Start next phase automatically
        # Generate phase reports
        # Update stakeholders
        pass

    async def handle_calendar_event_created(self, event_data: dict):
        """Handle calendar event creation"""
        logger.info(f"Calendar event created: {event_data}")
        
        # Check for conflicts
        # Send invitations
        # Set up reminders
        pass

    async def handle_calendar_conflict(self, event_data: dict):
        """Handle calendar conflict detection"""
        logger.warning(f"Calendar conflict detected: {event_data}")
        
        # Suggest alternative times
        # Notify affected parties
        # Auto-reschedule if possible
        pass

    async def handle_meeting_reminder(self, event_data: dict):
        """Handle meeting reminder"""
        logger.info(f"Sending meeting reminder: {event_data}")
        
        # Send multi-channel reminders
        # Update attendance tracking
        pass

    async def handle_resource_allocated(self, event_data: dict):
        """Handle resource allocation event"""
        logger.info(f"Resource allocated: {event_data}")
        
        # Update capacity planning
        # Check for over-allocation
        # Optimize resource distribution
        pass

    async def handle_resource_overallocation(self, event_data: dict):
        """Handle resource over-allocation"""
        logger.warning(f"Resource over-allocated: {event_data}")
        
        # Send alerts to managers
        # Suggest rebalancing
        # Update project timelines
        pass

    async def handle_team_member_added(self, event_data: dict):
        """Handle team member addition"""
        logger.info(f"Team member added: {event_data}")
        
        # Send welcome notifications
        # Update access permissions
        # Create onboarding tasks
        pass

    async def handle_project_message(self, event_data: dict):
        """Handle project message event"""
        logger.info(f"Project message sent: {event_data}")
        
        # Route to appropriate channels
        # Update communication logs
        # Check for action items
        pass

    async def handle_comment_added(self, event_data: dict):
        """Handle comment addition"""
        logger.info(f"Comment added: {event_data}")
        
        # Send notifications to subscribers
        # Update activity feeds
        # Check for mentions
        pass

    # Inter-module event handlers
    async def handle_employee_status_change(self, event_data: dict):
        """Handle employee status change from HR module"""
        logger.info(f"Employee status changed: {event_data}")
        
        # Update project team assignments
        # Reassign tasks if necessary
        # Update resource planning
        pass

    async def handle_employee_skill_update(self, event_data: dict):
        """Handle employee skill update from HR module"""
        logger.info(f"Employee skills updated: {event_data}")
        
        # Update resource matching algorithms
        # Suggest new project assignments
        pass

    async def handle_opportunity_won(self, event_data: dict):
        """Handle won opportunity from CRM module"""
        logger.info(f"Opportunity won: {event_data}")
        
        # Auto-create project from opportunity
        # Set up initial project structure
        # Assign team based on opportunity requirements
        pass

    async def handle_contact_created(self, event_data: dict):
        """Handle new contact from CRM module"""
        logger.info(f"New contact created: {event_data}")
        
        # Add to stakeholder database
        # Update project communication lists
        pass

    async def handle_budget_approved(self, event_data: dict):
        """Handle budget approval from Accounting module"""
        logger.info(f"Budget approved: {event_data}")
        
        # Update project financial constraints
        # Enable resource allocation
        # Start project execution phase
        pass

    async def handle_invoice_paid(self, event_data: dict):
        """Handle invoice payment from Accounting module"""
        logger.info(f"Invoice paid: {event_data}")
        
        # Update project revenue tracking
        # Trigger milestone payments
        # Update financial reports
        pass

    def get_module_routes(self):
        """Get API routes for this module"""
        from .api.v1.routes import projects, tasks, calendar, timeline, analytics
        
        return [
            projects.router,
            tasks.router,
            calendar.router,
            timeline.router,
            analytics.router,
        ]

    def get_module_dependencies(self) -> List[str]:
        """Get list of modules this module depends on"""
        return ["hr", "auth"]  # Basic dependencies

    def get_health_check(self) -> dict:
        """Return module health status"""
        return {
            "module": self.name,
            "version": self.version,
            "status": "healthy",
            "checks": {
                "database": True,
                "event_bus": True,
                "background_tasks": True,
            }
        }
