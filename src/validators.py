"""
JSON Schema validation engine for StandSpec AI V1.2 collector output and pipelines.
Ensures zero schema violations can be silently written to disk (Gate P0-1).
"""

import json
from pathlib import Path
from jsonschema import Draft202012Validator

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

_STANDARD_SCHEMA_PATH = SCHEMAS_DIR / "standard_v1_2.schema.json"
_REFERENCE_SCHEMA_PATH = SCHEMAS_DIR / "reference_v1_2.schema.json"

_standard_validator = None
_reference_validator = None


def _get_standard_validator() -> Draft202012Validator:
    global _standard_validator
    if _standard_validator is None:
        with open(_STANDARD_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        Draft202012Validator.check_schema(schema)
        _standard_validator = Draft202012Validator(schema)
    return _standard_validator


def _get_reference_validator() -> Draft202012Validator:
    global _reference_validator
    if _reference_validator is None:
        with open(_REFERENCE_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        Draft202012Validator.check_schema(schema)
        _reference_validator = Draft202012Validator(schema)
    return _reference_validator


def validate_standard_v1_2(record: dict) -> list[str]:
    """
    Validate a standard record against the V1.2 canonical schema.
    Returns a list of validation error descriptions. Empty list means valid.
    """
    validator = _get_standard_validator()
    errors = []
    for err in sorted(validator.iter_errors(record), key=lambda e: e.path):
        loc = ".".join(str(p) for p in err.path) if err.path else "root"
        errors.append(f"[{loc}] {err.message}")
    return errors


def validate_reference_v1_2(ref: dict) -> list[str]:
    """
    Validate a reference record against the V1.2 canonical schema.
    Returns a list of validation error descriptions. Empty list means valid.
    """
    validator = _get_reference_validator()
    errors = []
    for err in sorted(validator.iter_errors(ref), key=lambda e: e.path):
        loc = ".".join(str(p) for p in err.path) if err.path else "root"
        errors.append(f"[{loc}] {err.message}")
    return errors
