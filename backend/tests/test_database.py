import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event

from app.core.database import Base
from app.models import (
    Clause,
    ClauseAnalysisRecord,
    Contract,
    QAHistory,
    User,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    async_session = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session


@pytest.mark.anyio
async def test_user_creation_and_retrieval(db_session: AsyncSession):
    user = User(
        email="testuser@termshield.com",
        hashed_password="hashedpassword123",
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.commit()

    stmt = select(User).where(User.email == "testuser@termshield.com")
    result = await db_session.execute(stmt)
    retrieved = result.scalar_one_or_none()

    assert retrieved is not None
    assert retrieved.email == "testuser@termshield.com"
    assert retrieved.full_name == "Test User"
    assert retrieved.is_active is True
    assert retrieved.is_verified is False
    assert retrieved.created_at is not None


@pytest.mark.anyio
async def test_user_unique_email_constraint(db_session: AsyncSession):
    user1 = User(
        email="duplicate@termshield.com",
        full_name="First User",
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        email="duplicate@termshield.com",
        full_name="Second User",
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.anyio
async def test_contract_and_user_relationship(db_session: AsyncSession):
    user = User(
        email="owner@termshield.com",
        full_name="Contract Owner",
    )
    db_session.add(user)
    await db_session.commit()

    contract = Contract(
        id=str(uuid.uuid4()),
        user_id=user.id,
        filename="service_agreement.pdf",
        file_type="pdf",
        size_bytes=1048576,
        character_count=5200,
        status="analyzed",
        overall_risk="MEDIUM",
        overall_risk_score=45,
    )
    db_session.add(contract)
    await db_session.commit()

    # Query contract with user loaded
    stmt = select(Contract).where(Contract.id == contract.id)
    res = await db_session.execute(stmt)
    saved_contract = res.scalar_one()

    assert saved_contract.filename == "service_agreement.pdf"
    assert saved_contract.overall_risk == "MEDIUM"
    assert saved_contract.overall_risk_score == 45
    assert saved_contract.user_id == user.id


@pytest.mark.anyio
async def test_clauses_and_analysis_relationship(db_session: AsyncSession):
    contract_id = str(uuid.uuid4())
    contract = Contract(
        id=contract_id,
        filename="loan_agreement.pdf",
        file_type="pdf",
        size_bytes=2048,
        character_count=1200,
    )
    db_session.add(contract)
    await db_session.commit()

    clause_id = f"clause-{contract_id}-1"
    clause = Clause(
        id=clause_id,
        contract_id=contract_id,
        clause_number="1",
        title="Loan Facility",
        text="The Lender agrees to make available to the Borrower a term loan facility of 500,000 INR.",
        order=1,
        character_count=85,
        clause_type="PAYMENT",
    )
    db_session.add(clause)
    await db_session.commit()

    analysis = ClauseAnalysisRecord(
        contract_id=contract_id,
        clause_id=clause_id,
        clause_type="PAYMENT",
        risk_level="LOW",
        risk_score=15,
        meaning="The lender provides a 500,000 INR loan to the borrower.",
        analysis_data='{"parties": ["Lender", "Borrower"], "currencies": ["INR"], "monetary_terms": ["500,000 INR"]}',
    )
    db_session.add(analysis)
    await db_session.commit()

    # Verify retrieval
    stmt = select(Clause).where(Clause.id == clause_id)
    res = await db_session.execute(stmt)
    loaded_clause = res.scalar_one()

    assert loaded_clause.title == "Loan Facility"
    assert loaded_clause.clause_type == "PAYMENT"

    stmt_analysis = select(ClauseAnalysisRecord).where(ClauseAnalysisRecord.clause_id == clause_id)
    res_analysis = await db_session.execute(stmt_analysis)
    loaded_analysis = res_analysis.scalar_one()

    assert loaded_analysis.risk_level == "LOW"
    assert loaded_analysis.risk_score == 15
    assert "500,000 INR" in loaded_analysis.analysis_data


@pytest.mark.anyio
async def test_foreign_key_enforcement(db_session: AsyncSession):
    invalid_contract_id = str(uuid.uuid4())
    clause = Clause(
        id="invalid-clause-1",
        contract_id=invalid_contract_id,
        text="This should fail because contract_id does not exist.",
        order=1,
        character_count=50,
    )
    db_session.add(clause)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.anyio
async def test_cascading_delete(db_session: AsyncSession):
    contract_id = str(uuid.uuid4())
    contract = Contract(
        id=contract_id,
        filename="to_delete.pdf",
        file_type="pdf",
    )
    db_session.add(contract)
    await db_session.commit()

    clause_id = f"clause-{contract_id}-1"
    clause = Clause(
        id=clause_id,
        contract_id=contract_id,
        text="Clause text.",
        order=1,
        character_count=12,
    )
    db_session.add(clause)

    analysis = ClauseAnalysisRecord(
        contract_id=contract_id,
        clause_id=clause_id,
        risk_level="HIGH",
        risk_score=80,
    )
    db_session.add(analysis)

    qa = QAHistory(
        contract_id=contract_id,
        question="What is this clause?",
        answer="A sample clause.",
        confidence=0.95,
    )
    db_session.add(qa)
    await db_session.commit()

    # Now delete the contract
    await db_session.delete(contract)
    await db_session.commit()

    # Verify clauses, analyses, and qa_records are cascaded
    clause_res = await db_session.execute(select(Clause).where(Clause.contract_id == contract_id))
    assert clause_res.scalars().all() == []

    analysis_res = await db_session.execute(select(ClauseAnalysisRecord).where(ClauseAnalysisRecord.contract_id == contract_id))
    assert analysis_res.scalars().all() == []

    qa_res = await db_session.execute(select(QAHistory).where(QAHistory.contract_id == contract_id))
    assert qa_res.scalars().all() == []
