"""
API v1 route aggregator.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, users
from app.api.v1.endpoints import organizations, workspaces, projects, members
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.invitations import ws_router as invitations_ws_router
from app.api.v1.endpoints.invitations import router as invitations_router

api_v1_router = APIRouter()

# Health
api_v1_router.include_router(health.router, prefix="/health", tags=["health"])

# Auth
api_v1_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Users
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])

# Organizations
api_v1_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])

# Workspaces
api_v1_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])

# Members (nested under workspaces)
api_v1_router.include_router(members.router, prefix="/workspaces", tags=["workspaces"])

# Invitations (workspace-nested routes)
api_v1_router.include_router(invitations_ws_router, prefix="/workspaces", tags=["workspaces"])

# Invitations (standalone routes)
api_v1_router.include_router(invitations_router, prefix="", tags=["invitations"])

# Projects
api_v1_router.include_router(projects.router, prefix="/projects", tags=["projects"])

# Dashboard
api_v1_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
