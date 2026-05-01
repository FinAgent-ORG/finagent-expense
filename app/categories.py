from __future__ import annotations

BUSINESS_CATEGORIES = (
    "Operational",
    "Inventory",
    "Employee",
    "Logistics",
    "Marketing",
    "Software",
    "Utilities",
    "Travel",
    "Compliance",
    "Miscellaneous",
)

DEFAULT_CATEGORY = "Miscellaneous"

LEGACY_CATEGORY_MAP = {
    "entertainment": "Marketing",
    "food": "Operational",
    "groceries": "Inventory",
    "healthcare": "Employee",
    "other": "Miscellaneous",
    "rent": "Operational",
    "transport": "Travel",
    "utilities": "Utilities",
}

CATEGORY_ALIASES = {
    "operational": "Operational",
    "operations": "Operational",
    "office": "Operational",
    "inventory": "Inventory",
    "stock": "Inventory",
    "supplies": "Inventory",
    "materials": "Inventory",
    "employee": "Employee",
    "employees": "Employee",
    "payroll": "Employee",
    "salary": "Employee",
    "salaries": "Employee",
    "benefits": "Employee",
    "reimbursement": "Employee",
    "logistics": "Logistics",
    "shipping": "Logistics",
    "freight": "Logistics",
    "courier": "Logistics",
    "delivery": "Logistics",
    "warehouse": "Logistics",
    "fuel": "Logistics",
    "diesel": "Logistics",
    "petrol": "Logistics",
    "parking": "Logistics",
    "toll": "Logistics",
    "marketing": "Marketing",
    "advertising": "Marketing",
    "ads": "Marketing",
    "campaign": "Marketing",
    "branding": "Marketing",
    "promotion": "Marketing",
    "software": "Software",
    "saas": "Software",
    "license": "Software",
    "licensing": "Software",
    "subscription": "Software",
    "subscriptions": "Software",
    "cloud": "Software",
    "hosting": "Software",
    "utilities": "Utilities",
    "electricity": "Utilities",
    "water": "Utilities",
    "internet": "Utilities",
    "wifi": "Utilities",
    "broadband": "Utilities",
    "gas": "Utilities",
    "phone": "Utilities",
    "travel": "Travel",
    "trip": "Travel",
    "flight": "Travel",
    "airfare": "Travel",
    "hotel": "Travel",
    "lodging": "Travel",
    "taxi": "Travel",
    "uber": "Travel",
    "ola": "Travel",
    "bus": "Travel",
    "train": "Travel",
    "metro": "Travel",
    "cab": "Travel",
    "compliance": "Compliance",
    "legal": "Compliance",
    "audit": "Compliance",
    "tax": "Compliance",
    "filing": "Compliance",
    "insurance": "Compliance",
    "misc": "Miscellaneous",
    "miscellaneous": "Miscellaneous",
    "general": "Miscellaneous",
    "uncategorized": "Miscellaneous",
}


def normalize_expense_category(value: str | None) -> str:
    if value is None:
        return DEFAULT_CATEGORY

    cleaned = " ".join(str(value).strip().split())
    if not cleaned:
        return DEFAULT_CATEGORY

    if cleaned in BUSINESS_CATEGORIES:
        return cleaned

    lowered = cleaned.lower()
    if lowered in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[lowered]

    if lowered in LEGACY_CATEGORY_MAP:
        return LEGACY_CATEGORY_MAP[lowered]

    return DEFAULT_CATEGORY
