import base64
import json
import os
from datetime import date
from io import BytesIO

import httpx
from pypdf import PdfReader

from schemas import ExpenseCategory, ExpenseExtractionResponse, ExtractedExpense

IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
TEXT_CONTENT_TYPES = {
    "application/csv",
    "application/json",
    "application/pdf",
    "text/csv",
    "text/plain",
}


def _image_extraction_enabled() -> bool:
    return os.getenv("OLLAMA_IMAGE_EXTRACTION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


CATEGORY_ALIASES = {
    "entertainment": ExpenseCategory.ENTERTAINMENT,
    "food": ExpenseCategory.FOOD,
    "groceries": ExpenseCategory.GROCERIES,
    "health": ExpenseCategory.HEALTHCARE,
    "healthcare": ExpenseCategory.HEALTHCARE,
    "other": ExpenseCategory.OTHER,
    "rent": ExpenseCategory.RENT,
    "transport": ExpenseCategory.TRANSPORT,
    "travel": ExpenseCategory.TRANSPORT,
    "utilities": ExpenseCategory.UTILITIES,
}


def _clean_json_response(raw_text: str) -> str:
    trimmed = raw_text.strip()
    if trimmed.startswith("```"):
        lines = [line for line in trimmed.splitlines() if not line.startswith("```")]
        trimmed = "\n".join(lines).strip()
    return trimmed


def _normalize_category(value: str | None) -> ExpenseCategory:
    if not value:
        return ExpenseCategory.OTHER
    normalized = value.strip().lower()
    return CATEGORY_ALIASES.get(normalized, ExpenseCategory.OTHER)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _build_response(payload: dict, filename: str, source_type: str) -> ExpenseExtractionResponse:
    raw_expenses = payload.get("expenses", [])
    notes = [str(note).strip() for note in payload.get("notes", []) if str(note).strip()]
    parsed_expenses: list[ExtractedExpense] = []

    for item in raw_expenses:
        try:
            parsed_expenses.append(
                ExtractedExpense(
                    amount=float(item.get("amount", 0)),
                    currency=str(item.get("currency", "INR")),
                    category=_normalize_category(item.get("category")).value,
                    description=str(item.get("description", "")),
                    expense_date=_parse_date(item.get("expense_date")),
                    confidence=float(item.get("confidence", 0.0)),
                )
            )
        except Exception:
            continue

    if not parsed_expenses and not notes:
        notes = ["No clear expenses could be extracted from the uploaded document."]

    return ExpenseExtractionResponse(
        filename=filename,
        source_type=source_type,
        expenses=parsed_expenses,
        notes=notes,
    )


async def _call_ollama(prompt: str, *, images: list[str] | None = None, model: str | None = None) -> dict:
    payload = {
        "model": model or os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
        "prompt": prompt,
        "stream": False,
    }
    if images:
        payload["images"] = images

    async with httpx.AsyncClient(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), timeout=90.0) as client:
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        response_text = _clean_json_response(str(data.get("response", "")))
        return json.loads(response_text)


def _extract_text_payload(file_bytes: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        reader = PdfReader(BytesIO(file_bytes))
        return "\n".join((page.extract_text() or "").strip() for page in reader.pages if page.extract_text())
    return file_bytes.decode("utf-8", errors="ignore")


async def extract_expenses_from_upload(filename: str, content_type: str, file_bytes: bytes) -> ExpenseExtractionResponse:
    prompt = (
        "You are an expense extraction assistant. "
        "Extract every real expense you can identify and return strict JSON with this exact structure: "
        '{"expenses":[{"amount":123.45,"currency":"INR","category":"Food","description":"Lunch","expense_date":"2026-04-23","confidence":0.92}],"notes":["short note"]}. '
        "Use one of these categories only: Food, Transport, Utilities, Entertainment, Groceries, Rent, Healthcare, Other. "
        "If a field is unknown, use sensible defaults: currency INR, category Other, expense_date null. "
        "Do not include markdown or extra commentary."
    )

    if content_type in IMAGE_CONTENT_TYPES:
        if not _image_extraction_enabled():
            return ExpenseExtractionResponse(
                filename=filename,
                source_type="image",
                expenses=[],
                notes=[
                    "Image receipt extraction is disabled in the current CPU-only deployment. "
                    "Upload a PDF, text, CSV, or JSON file instead."
                ],
            )
        payload = await _call_ollama(
            f"{prompt} The uploaded receipt or image is attached. Extract expenses visible in the image.",
            images=[base64.b64encode(file_bytes).decode("utf-8")],
            model=os.getenv("OLLAMA_VISION_MODEL") or os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
        )
        return _build_response(payload, filename, "image")

    if content_type in TEXT_CONTENT_TYPES:
        text_payload = _extract_text_payload(file_bytes, content_type)
        payload = await _call_ollama(
            f"{prompt}\n\nHere is the document content:\n{text_payload[:12000]}",
            model=os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
        )
        source_type = "pdf" if content_type == "application/pdf" else "document"
        return _build_response(payload, filename, source_type)

    return ExpenseExtractionResponse(
        filename=filename,
        source_type=content_type or "unknown",
        expenses=[],
        notes=["Unsupported file type. Upload a receipt image, PDF, text, CSV, or JSON file."],
    )
