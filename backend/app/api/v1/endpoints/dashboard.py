"""
Dashboard statistics endpoint.

Provides aggregate counts for the authenticated user's dashboard.
Uses efficient aggregate queries to avoid N+1 patterns.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.core.logging import get_logger
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember

logger = get_logger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Return aggregate counts for the authenticated user's dashboard.

    Returns:
        Dict with org_count, workspace_count, project_count, member_count.
        All counts are scoped to entities the user owns or belongs to.
    """
    # User's organizations (where they are owner)
    org_count_result = await db.execute(
        select(func.count(Organization.id)).where(
            Organization.owner_id == user.id
        )
    )
    org_count = org_count_result.scalar() or 0

    # Workspaces the user is a member of
    ws_count_result = await db.execute(
        select(func.count(Workspace.id))
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )
    workspace_count = ws_count_result.scalar() or 0

    # Projects in workspaces the user belongs to
    proj_count_result = await db.execute(
        select(func.count(Project.id))
        .join(Workspace, Project.workspace_id == Workspace.id)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .where(Project.status == "active")
    )
    project_count = proj_count_result.scalar() or 0

    # Total members across all user's workspaces (distinct users)
    member_count_result = await db.execute(
        select(func.count(func.distinct(WorkspaceMember.user_id)))
        .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
        .join(Organization, Workspace.organization_id == Organization.id)
        .where(Organization.owner_id == user.id)
    )
    member_count = member_count_result.scalar() or 0

    return {
        "org_count": org_count,
        "workspace_count": workspace_count,
        "project_count": project_count,
        "member_count": member_count,
    }
