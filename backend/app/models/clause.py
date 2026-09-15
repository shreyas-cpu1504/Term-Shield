from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.clause_analysis import ClauseAnalysisRecord
    from app.models.contract import Contract


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        index=True,
    )
    contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    character_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    parent_clause: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    clause_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="clauses",
    )
    analysis: Mapped[Optional["ClauseAnalysisRecord"]] = relationship(
        "ClauseAnalysisRecord",
        back_populates="clause",
        uselist=False,
        cascade="all, delete-orphan",
    )
