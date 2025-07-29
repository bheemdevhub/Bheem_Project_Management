# Project Management Module

## Overview

The Project Management Module is a comprehensive solution for managing projects, tasks, timelines, resources, and team collaboration within the ERP system. It provides features for project planning, execution, monitoring, and reporting.

## Features

### Core Functionality

- **Project Management**: Create, update, and manage projects with full lifecycle support
- **Task Management**: Task creation, assignment, tracking, and completion
- **Timeline Management**: Project phases, milestones, and deadline tracking
- **Resource Management**: Team allocation, capacity planning, and utilization tracking
- **Calendar Integration**: Universal calendar with meeting scheduling and conflict detection
- **Analytics & Reporting**: Comprehensive analytics, productivity metrics, and custom reports

### Key Capabilities

1. **Project Lifecycle Management**
   - Project creation and configuration
   - Status tracking (Planning, Active, On Hold, Completed, Cancelled)
   - Budget management and tracking
   - Team member assignment and role management

2. **Task & Work Management**
   - Task creation with priorities, due dates, and assignments
   - Task dependencies and sequencing
   - Time tracking and logging
   - Progress monitoring and status updates

3. **Timeline & Scheduling**
   - Project phases and milestone management
   - Critical path calculation
   - Deadline monitoring and alerts
   - Gantt chart support

4. **Resource Planning**
   - Team capacity planning
   - Resource allocation optimization
   - Utilization tracking and reporting
   - Conflict detection and resolution

5. **Communication & Collaboration**
   - Project comments and discussions
   - Team messaging and notifications
   - File sharing and document management
   - Meeting scheduling and management

6. **Analytics & Insights**
   - Project health scoring
   - Productivity metrics
   - Budget utilization analysis
   - Team performance tracking
   - Custom dashboard and reports

## API Endpoints

### Projects
- `GET /project-management/projects/` - Get all projects
- `POST /project-management/projects/` - Create new project
- `GET /project-management/projects/{id}` - Get project details
- `PUT /project-management/projects/{id}` - Update project
- `DELETE /project-management/projects/{id}` - Delete project
- `GET /project-management/projects/{id}/tasks/` - Get project tasks
- `GET /project-management/projects/{id}/budget/` - Get project budget
- `POST /project-management/projects/{id}/team-members/` - Add team member

### Tasks
- `GET /project-management/tasks/` - Get all tasks
- `POST /project-management/tasks/` - Create new task
- `PUT /project-management/tasks/{id}` - Update task
- `DELETE /project-management/tasks/{id}` - Delete task
- `POST /project-management/tasks/{id}/comments/` - Add task comment
- `GET /project-management/tasks/{id}/time-logs/` - Get time logs
- `POST /project-management/tasks/{id}/time-logs/` - Log time
- `PUT /project-management/tasks/{id}/assign` - Assign task

### Calendar
- `GET /project-management/calendar/events/` - Get calendar events
- `POST /project-management/calendar/events/` - Create calendar event
- `PUT /project-management/calendar/events/{id}` - Update event
- `DELETE /project-management/calendar/events/{id}` - Delete event
- `GET /project-management/calendar/conflicts/` - Check conflicts
- `POST /project-management/calendar/sync/` - Sync external calendar

### Timeline
- `GET /project-management/projects/{id}/timeline/` - Get project timeline
- `POST /project-management/projects/{id}/phases/` - Create project phase
- `PUT /project-management/phases/{id}` - Update phase
- `POST /project-management/milestones/` - Create milestone
- `PUT /project-management/milestones/{id}/complete` - Complete milestone

### Analytics
- `GET /project-management/analytics/dashboard/` - Get analytics dashboard
- `GET /project-management/analytics/productivity/` - Get productivity metrics
- `GET /project-management/analytics/budget-utilization/` - Get budget metrics
- `GET /project-management/analytics/team-performance/` - Get team performance

## Event System

The module subscribes to and publishes various events for integration with other modules:

### Published Events
- `project.created` - When a new project is created
- `project.status_changed` - When project status changes
- `task.assigned` - When a task is assigned to someone
- `task.completed` - When a task is completed
- `milestone.completed` - When a milestone is achieved
- `deadline.approaching` - When deadlines are approaching
- `calendar.conflict.detected` - When calendar conflicts are found

### Subscribed Events
- `hr.employee.status_changed` - Updates team assignments
- `crm.opportunity.won` - Auto-creates projects from opportunities
- `accounting.budget.approved` - Enables project resource allocation

## Background Tasks

The module includes several background tasks for automation:

- **Deadline Monitoring** (Hourly): Check for approaching deadlines and send alerts
- **Health Score Updates** (Daily): Calculate and update project health metrics
- **Timeline Reports** (Weekly): Generate project progress reports
- **Calendar Sync** (Every 4 hours): Sync with external calendar systems
- **Milestone Reminders** (Daily): Send reminders for upcoming milestones
- **Phase Updates** (Daily): Auto-update project phase completion
- **Data Cleanup** (Weekly): Clean up old notifications and temporary data
- **Productivity Reports** (Weekly): Generate team productivity analytics
- **Data Backup** (Daily): Backup critical project data
- **Resource Optimization** (Weekly): Optimize resource allocation

## Configuration

Key configuration options:

```python
# Deadline warning thresholds
DEADLINE_WARNING_DAYS = [1, 3, 7]

# Default working hours
DEFAULT_WORKING_HOURS_START = 9  # 9 AM
DEFAULT_WORKING_HOURS_END = 17   # 5 PM

# File upload limits
MAX_FILE_SIZE_MB = 50
ALLOWED_FILE_TYPES = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']

# Performance settings
MAX_PROJECTS_PER_PAGE = 50
MAX_TASKS_PER_PROJECT = 1000
```

## Permissions

The module defines granular permissions for different operations:

- `pm.create_project` - Create new projects
- `pm.update_project` - Modify existing projects
- `pm.view_project` - View project details
- `pm.delete_project` - Delete projects
- `pm.assign_task` - Assign tasks to team members
- `pm.log_time` - Log time against tasks
- `pm.manage_calendar` - Manage calendar events
- `pm.view_analytics` - Access analytics and reports
- `pm.manage_module_settings` - Configure module settings

## Integration

### HR Module Integration
- Automatic team member synchronization
- Skill-based resource matching
- Capacity planning based on employee availability

### CRM Module Integration
- Auto-project creation from won opportunities
- Client communication tracking
- Stakeholder management

### Accounting Module Integration
- Budget approval workflows
- Financial tracking and reporting
- Cost center allocation

## Installation

1. The module is automatically loaded when the ERP system starts
2. Database migrations are applied automatically
3. Background tasks are scheduled automatically
4. API routes are registered with the main application

## Usage Examples

### Creating a Project
```python
project_data = {
    "name": "Website Redesign",
    "description": "Complete redesign of company website",
    "start_date": "2024-07-01",
    "end_date": "2024-12-31",
    "budget": 50000,
    "priority": "high"
}
project = service.create_project(project_data, creator_id=1)
```

### Assigning a Task
```python
task_data = {
    "title": "Create wireframes",
    "description": "Design wireframes for main pages",
    "project_id": 1,
    "due_date": "2024-07-15",
    "priority": "high",
    "estimated_hours": 16
}
task = service.create_task(task_data, creator_id=1)
service.assign_task(task.id, assignee_id=5)
```

### Scheduling a Meeting
```python
event_data = {
    "title": "Project Kickoff Meeting",
    "description": "Initial project planning meeting",
    "start_datetime": "2024-07-01T10:00:00Z",
    "end_datetime": "2024-07-01T11:30:00Z",
    "attendee_ids": [1, 2, 3, 4, 5]
}
event = service.create_calendar_event(event_data, creator_id=1)
```

## Support

For issues or questions regarding the Project Management module:

1. Check the API documentation for endpoint details
2. Review the event system for integration possibilities
3. Consult the configuration options for customization
4. Contact the development team for technical support
