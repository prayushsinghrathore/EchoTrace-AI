"""API v1 route aggregator."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, members, organizations, projects, users, workspaces
from app.api.v1.endpoints.ai import router as ai_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.evidence import router as evidence_router
from app.api.v1.endpoints.investigations import router as investigations_router
from app.api.v1.endpoints.invitations import router as invitations_router
from app.api.v1.endpoints.invitations import ws_router as invitations_ws_router

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, prefix="/health", tags=["health"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_v1_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_v1_router.include_router(members.router, prefix="/workspaces", tags=["workspaces"])
api_v1_router.include_router(invitations_ws_router, prefix="/workspaces", tags=["workspaces"])
api_v1_router.include_router(invitations_router, prefix="", tags=["invitations"])
api_v1_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_v1_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_v1_router.include_router(evidence_router, prefix="/evidence", tags=["evidence"])
api_v1_router.include_router(investigations_router, prefix="/investigations", tags=["investigations"])
api_v1_router.include_router(ai_router, prefix="/ai", tags=["ai"])
