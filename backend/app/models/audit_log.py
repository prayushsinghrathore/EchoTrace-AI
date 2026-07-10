"""
AuditLog model — immutable enterprise audit trail for all significant actions.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    WORKSPACE_CREATED = "workspace_created"
    WORKSPACE_UPDATED = "workspace_updated"
    WORKSPACE_DELETED = "workspace_deleted"
    EVIDENCE_CREATED = "evidence_created"
    EVIDENCE_UPLOADED = "evidence_uploaded"
    EVIDENCE_VERIFIED = "evidence_verified"
    EVIDENCE_DELETED = "evidence_deleted"
    INVESTIGATION_CREATED = "investigation_created"
    INVESTIGATION_UPDATED = "investigation_updated"
    INVESTIGATION_CLOSED = "investigation_closed"
    AI_JOB_COMPLETED = "ai_job_completed"
    EXPORT_CREATED = "export_created"
    EXPORT_DOWNLOADED = "export_downloaded"
    REPORT_GENERATED = "report_generated"
    ENTITY_APPROVED = "entity_approved"
    ENTITY_REJECTED = "entity_rejected"
    RELATIONSHIP_APPROVED = "relationship_approved"
    RELATIONSHIP_REJECTED = "relationship_rejected"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    MEMBER_ROLE_CHANGED = "member_role_changed"
    ROLE_CHANGED = "role_changed"
    PERMISSION_CHANGED = "permission_changed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = ({"comment": "Immutable enterprise audit trail"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"), nullable=False, index=True
    )
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action.value} user={self.user_id}>"
