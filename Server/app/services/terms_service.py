"""
PURPOSE:
Manages persistent term configuration in services/terms.json with validation
and atomic writes.

API ENDPOINTS USED:
- None directly. Called by GET /terms and PUT /terms.
"""

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


_TERMS_FILE = Path(__file__).with_name("terms.json")
_LOCK = threading.Lock()


def _default_terms_payload() -> dict[str, Any]:
    return {
        "_comment": "This file stores admin-managed analytics terms.",
        "_comment_date_format": "Use YYYY-MM-DD, for example 2026-01-01 and 2026-04-30.",
        "terms": [],
    }


def _read_payload() -> dict[str, Any]:
    if not _TERMS_FILE.exists():
        payload = _default_terms_payload()
        _atomic_write(payload)
        return payload

    with _TERMS_FILE.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("terms.json must contain a JSON object")

    if "terms" not in payload:
        payload["terms"] = []

    if not isinstance(payload["terms"], list):
        raise ValueError("'terms' must be a list")

    return payload


def _atomic_write(payload: dict[str, Any]) -> None:
    _TERMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=_TERMS_FILE.parent, encoding="utf-8") as tmp:
        json.dump(payload, tmp, indent=2)
        tmp.write("\n")
        temp_name = tmp.name

    os.replace(temp_name, _TERMS_FILE)


def _validate_term(term: dict[str, str]) -> None:
    required = ("id", "name", "start", "end")
    for key in required:
        value = term.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Term field '{key}' is required")

    try:
        start_date = datetime.strptime(term["start"], "%Y-%m-%d").date()
        end_date = datetime.strptime(term["end"], "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Term dates must use YYYY-MM-DD") from exc

    if end_date < start_date:
        raise ValueError(f"Term '{term['id']}' has end date before start date")


def _validate_terms(terms: list[dict[str, str]]) -> None:
    seen_ids = set()
    for term in terms:
        _validate_term(term)

        term_id = term["id"].strip()
        if term_id in seen_ids:
            raise ValueError(f"Duplicate term id '{term_id}'")
        seen_ids.add(term_id)


def get_terms() -> list[dict[str, str]]:
    with _LOCK:
        payload = _read_payload()
        terms = payload.get("terms", [])
        _validate_terms(terms)
        return terms


def set_terms(terms: list[dict[str, str]]) -> list[dict[str, str]]:
    with _LOCK:
        normalized_terms = []
        for term in terms:
            normalized_terms.append(
                {
                    "id": term["id"].strip(),
                    "name": term["name"].strip(),
                    "start": term["start"].strip(),
                    "end": term["end"].strip(),
                }
            )

        _validate_terms(normalized_terms)

        payload = _read_payload()
        payload["terms"] = normalized_terms
        payload.setdefault("_comment", "This file stores admin-managed analytics terms.")
        payload.setdefault(
            "_comment_date_format",
            "Use YYYY-MM-DD, for example 2026-01-01 and 2026-04-30.",
        )
        _atomic_write(payload)
        return normalized_terms


def get_term_by_id(term_id: str) -> dict[str, str] | None:
    terms = get_terms()
    for term in terms:
        if term["id"] == term_id:
            return term
    return None
