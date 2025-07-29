
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from fastapi import HTTPException
from app.modules.project_management.core.models.project_models import ProjectPhase
from app.modules.project_management.core.schemas.project_phase_schemas import (
    ProjectPhaseCreate, ProjectPhaseUpdate
)
from app.core.event_bus import EventBus

class ProjectPhaseService:
    def __init__(self, db: AsyncSession, event_bus: Optional[EventBus] = None):
        self.db = db
        self.event_bus = event_bus

    async def create_phase(self, data: ProjectPhaseCreate) -> ProjectPhase:
        phase = ProjectPhase(**data.dict())
        self.db.add(phase)
        await self.db.commit()
        await self.db.refresh(phase)
        if self.event_bus:
            await self.event_bus.publish("PHASE_CREATED", {"phase_id": str(phase.id)})
        return phase

    async def get_phase(self, phase_id: UUID) -> ProjectPhase:
        result = await self.db.execute(select(ProjectPhase).where(ProjectPhase.id == phase_id))
        phase = result.scalar_one_or_none()
        if not phase:
            raise HTTPException(status_code=404, detail="Project phase not found")
        return phase

    async def list_phases(self, project_id: UUID) -> List[ProjectPhase]:
        result = await self.db.execute(select(ProjectPhase).where(ProjectPhase.project_id == project_id))
        return result.scalars().all()

    async def update_phase(self, phase_id: UUID, data: ProjectPhaseUpdate) -> ProjectPhase:
        phase = await self.get_phase(phase_id)
        for field, value in data.dict(exclude_unset=True).items():
            setattr(phase, field, value)
        await self.db.commit()
        await self.db.refresh(phase)
        if self.event_bus:
            await self.event_bus.publish("PHASE_UPDATED", {"phase_id": str(phase.id)})
        return phase

    async def delete_phase(self, phase_id: UUID) -> None:
        phase = await self.get_phase(phase_id)
        await self.db.delete(phase)
        await self.db.commit()
        if self.event_bus:
            await self.event_bus.publish("PHASE_DELETED", {"phase_id": str(phase_id)})
        return None
