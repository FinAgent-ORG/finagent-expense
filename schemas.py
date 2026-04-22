from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseCategory(str, Enum):
    FOOD = "Food"
    TRANSPORT = "Transport"
    UTILITIES = "Utilities"
    ENTERTAINMENT = "Entertainment"
    GROCERIES = "Groceries"
    RENT = "Rent"
    HEALTHCARE = "Healthcare"
    OTHER = "Other"


class ExpenseCreate(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    category: ExpenseCategory
    description: str = Field(min_length=1, max_length=500)
    expense_date: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return " ".join(value.strip().split())


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    amount: float
    currency: str
    category: str
    description: str
    expense_date: date


class ExpenseTotals(BaseModel):
    today: float
    month: float
    year: float
