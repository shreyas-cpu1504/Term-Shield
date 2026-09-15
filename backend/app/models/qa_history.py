import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contract import Contract
    from app.models.user import User


class QAHistory(Base):
    __tablename__ = "qa_history"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    question: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )
    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="qa_records",
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="qa_history",
    )
