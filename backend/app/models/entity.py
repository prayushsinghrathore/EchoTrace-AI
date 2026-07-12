"""Entity model — people, devices, IPs, domains, etc."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.investigation import Investigation
    from app.models.relationship import Relationship

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class EntityType(str, enum.Enum):
    PERSON = "person"
    EMAIL = "email"
    PHONE = "phone"
    DEVICE = "device"
    FILE = "file"
    DOMAIN = "domain"
    URL = "url"
    IP = "ip"
    HASH = "hash"
    ACCOUNT = "account"
    VEHICLE = "vehicle"
    LOCATION = "location"
    BANK_ACCOUNT = "bank_account"
    CRYPTO_WALLET = "crypto_wallet"
    CUSTOM = "custom"


class Entity(Base, TimestampMixin):
    __tablename__ = "entities"
    __table_args__ = ({"comment": "Entities within investigations"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[EntityType] = mapped_column(SAEnum(EntityType, name="entity_type", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    investigation: Mapped[Investigation] = relationship(back_populates="entities")
    src_rels: Mapped[list[Relationship]] = relationship(back_populates="src_entity", cascade="all, delete-orphan", passive_deletes=True, foreign_keys="Relationship.source_entity_id")
    tgt_rels: Mapped[list[Relationship]] = relationship(back_populates="tgt_entity", cascade="all, delete-orphan", passive_deletes=True, foreign_keys="Relationship.target_entity_id")

    def __repr__(self):
        return f"<Entity id={self.id} type={self.type.value} label={self.label}>"
