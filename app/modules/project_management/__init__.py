# app/modules/project_management/__init__.py
"""Project Management Module Package"""

from .module import ProjectManagementModule
from .core.models.project_models import Project, Task, ProjectPhase

# Import unified models for easy access
from app.shared.models import Activity, FinancialDocument, Rating, Tag

__all__ = [
    'ProjectManagementModule',
    'Project', 'Task', 'ProjectPhase',
    'Activity', 'FinancialDocument', 'Rating', 'Tag'
]
