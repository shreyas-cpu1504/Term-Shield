import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.clause import Clause
    from app.models.clause_analysis import ClauseAnalysisRecord
    from app.models.qa_history import QAHistory
    from app.models.user import User


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pdf",
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    character_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="analyzed",
        index=True,
    )
    overall_risk: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="LOW",
        index=True,
    )
    overall_risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    summary_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    extracted_text_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="contracts",
    )
    clauses: Mapped[list["Clause"]] = relationship(
        "Clause",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="Clause.order",
    )
    analyses: Mapped[list["ClauseAnalysisRecord"]] = relationship(
        "ClauseAnalysisRecord",
        back_populates="contract",
        cascade="all, delete-orphan",
    )
    qa_records: Mapped[list["QAHistory"]] = relationship(
        "QAHistory",
        back_populates="contract",
        cascade="all, delete-orphan",
    )
