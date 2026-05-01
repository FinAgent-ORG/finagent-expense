from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .categories import DEFAULT_CATEGORY, normalize_expense_category


class ExpenseCategory(str, Enum):
    OPERATIONAL = "Operational"
    INVENTORY = "Inventory"
    EMPLOYEE = "Employee"
    LOGISTICS = "Logistics"
    MARKETING = "Marketing"
    SOFTWARE = "Software"
    UTILITIES = "Utilities"
    TRAVEL = "Travel"
    COMPLIANCE = "Compliance"
    MISCELLANEOUS = DEFAULT_CATEGORY


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

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: ExpenseCategory | str | None) -> ExpenseCategory:
        if isinstance(value, ExpenseCategory):
            return value
        return ExpenseCategory(normalize_expense_category(value))

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


class ExtractedExpense(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    category: ExpenseCategory
    description: str = Field(min_length=1, max_length=500)
    expense_date: date | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)

    @field_validator("currency")
    @classmethod
    def normalize_extract_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("category", mode="before")
    @classmethod
    def normalize_extract_category(cls, value: ExpenseCategory | str | None) -> ExpenseCategory:
        if isinstance(value, ExpenseCategory):
            return value
        return ExpenseCategory(normalize_expense_category(value))

    @field_validator("description")
    @classmethod
    def clean_extract_description(cls, value: str) -> str:
        return " ".join(value.strip().split())


class ExpenseExtractionResponse(BaseModel):
    filename: str
    source_type: str
    expenses: list[ExtractedExpense] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
