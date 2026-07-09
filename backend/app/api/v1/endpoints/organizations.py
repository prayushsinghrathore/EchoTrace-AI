"""Organization API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationResponse, OrganizationUpdate
from app.services.organization_service import OrganizationService

router = APIRouter(tags=["organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    body: OrganizationCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = OrganizationService(db)
    return await svc.create(name=body.name, slug=body.slug, owner_id=user.id, description=body.description)


@router.get("", response_model=list[OrganizationResponse])
async def list_orgs(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = OrganizationService(db)
    return await svc.list_for_user(user.id)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_org(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
):
    svc = OrganizationService(db)
    return await svc.get(org_id)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_org(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = OrganizationService(db)
    return await svc.update(org_id, user.id, **body.model_dump(exclude_none=True))


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_org(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = OrganizationService(db)
    await svc.delete(org_id, user.id)
