import os
import time
from collections import defaultdict, deque
from datetime import date
from typing import Annotated

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Base, engine, get_db
from .extractor import extract_expenses_from_upload
from .models import Expense
from .schemas import ExpenseCreate, ExpenseExtractionResponse, ExpenseResponse, ExpenseTotals
from .security import require_user

load_dotenv()

app = FastAPI(title=os.getenv("APP_NAME", "finagent-expense-service"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

_request_log: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = (
        request.headers.get("x-forwarded-for")
        or request.headers.get("x-real-ip")
        or request.client.host
        or "anonymous"
    ).split(",")[0].strip()
    now = time.time()
    window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    limit = int(os.getenv("RATE_LIMIT_REQUESTS", "120"))
    bucket = _request_log[client_ip]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded.")
    bucket.append(now)
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/api/v1/expenses/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/expenses", status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate,
    current_user: Annotated[dict, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExpenseResponse:
    expense = Expense(
        user_id=current_user["sub"],
        amount=payload.amount,
        currency=payload.currency,
        category=payload.category.value,
        description=payload.description,
        expense_date=payload.expense_date or date.today(),
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return ExpenseResponse.model_validate(expense)


@app.post("/api/v1/expenses/extract")
async def extract_expenses(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[dict, Depends(require_user)],
) -> ExpenseExtractionResponse:
    del current_user
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded file is too large.")

    try:
        return await extract_expenses_from_upload(file.filename or "upload", file.content_type or "", content)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to reach the extraction model.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to extract expenses from the uploaded file.") from exc


@app.get("/api/v1/expenses")
async def list_expenses(
    current_user: Annotated[dict, Depends(require_user)],
    days: Annotated[int | None, Query(default=None, ge=1, le=365)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ExpenseResponse]:
    stmt = select(Expense).where(Expense.user_id == current_user["sub"]).order_by(Expense.expense_date.desc())
    if days is not None:
        cutoff = date.today().toordinal() - days
        stmt = stmt.where(Expense.expense_date >= date.fromordinal(cutoff))
    rows = (await db.scalars(stmt)).all()
    return [ExpenseResponse.model_validate(row) for row in rows]


@app.get("/api/v1/expenses/totals")
async def get_totals(
    current_user: Annotated[dict, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExpenseTotals:
    today = date.today()
    user_id = current_user["sub"]

    today_total = await db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.user_id == user_id,
            Expense.expense_date == today,
        )
    )
    month_total = await db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.user_id == user_id,
            extract("year", Expense.expense_date) == today.year,
            extract("month", Expense.expense_date) == today.month,
        )
    )
    year_total = await db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.user_id == user_id,
            extract("year", Expense.expense_date) == today.year,
        )
    )

    return ExpenseTotals(today=float(today_total or 0), month=float(month_total or 0), year=float(year_total or 0))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=os.getenv("APP_HOST", "0.0.0.0"), port=int(os.getenv("APP_PORT", "8002")), reload=True)
