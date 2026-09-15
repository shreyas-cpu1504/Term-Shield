import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.clause import Clause
    from app.models.contract import Contract


class ClauseAnalysisRecord(Base):
    __tablename__ = "clause_analyses"

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
    clause_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("clauses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="LOW",
        index=True,
    )
    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    meaning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    analysis_data: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="analyses",
    )
    clause: Mapped["Clause"] = relationship(
        "Clause",
        back_populates="analysis",
    )
