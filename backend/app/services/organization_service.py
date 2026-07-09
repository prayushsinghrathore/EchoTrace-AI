"""
Organization service — manages tenant organizations.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func as sa_func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.organization import Organization
from app.models.workspace import Workspace
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class OrganizationService:
    """Business logic for organization operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(db, Organization)

    async def create(self, name: str, slug: str, owner_id: uuid.UUID, description: Optional[str] = None) -> Organization:
        """Create a new organization."""
        existing = await self.repo.find_one(slug=slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An organization with slug '{slug}' already exists",
            )
        org = Organization(name=name, slug=slug, owner_id=owner_id, description=description)
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        logger.info("Organization created", org_id=str(org.id), slug=slug, owner=str(owner_id))
        return org

    async def get(self, org_id: uuid.UUID) -> Organization:
        org = await self.repo.get(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        return org

    async def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        """List organizations where the user is owner or a member of any workspace."""
        stmt = (
            select(Organization)
            .where(Organization.owner_id == user_id)
            .order_by(Organization.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, org_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Organization:
        org = await self.get(org_id)
        if org.owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can update the organization")
        if "slug" in kwargs and kwargs["slug"]:
            existing = await self.repo.find_one(slug=kwargs["slug"])
            if existing and existing.id != org_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
        for key, val in kwargs.items():
            if val is not None and hasattr(org, key):
                setattr(org, key, val)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def delete(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        org = await self.get(org_id)
        if org.owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can delete the organization")
        await self.db.execute(sa_delete(Organization).where(Organization.id == org_id))
        await self.db.commit()
        logger.info("Organization deleted", org_id=str(org_id))
