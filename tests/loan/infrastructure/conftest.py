from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from library.loan.domain import Loan, LoanRepository
from library.loan.infrastructure import InMemoryLoanRepository, SqlLoanRepository
from library.shared.infrastructure import metadata


@pytest.fixture
async def sql_loan_repo() -> AsyncGenerator[SqlLoanRepository, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlLoanRepository(session)
    await session.close()
    await engine.dispose()


@pytest.fixture(params=["in_memory", "sql"])
async def empty_loan_repo(
    request, sql_loan_repo: SqlLoanRepository
) -> AsyncGenerator[LoanRepository, None]:
    if request.param == "in_memory":
        yield InMemoryLoanRepository()
    elif request.param == "sql":
        yield sql_loan_repo


@pytest.fixture
async def loan_repo_with_loan(
    empty_loan_repo: LoanRepository, valid_loan: Loan
) -> LoanRepository:
    """Repository з одним попередньо збереженим valid_loan."""
    await empty_loan_repo.create(valid_loan)
    return empty_loan_repo
