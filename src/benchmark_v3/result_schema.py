from __future__ import annotations

VALID_EVIDENCE_STATUS = {"REPRODUCED", "VERIFIED_FROM_RELEASE", "PARTIALLY_REPRODUCED", "NOT_RUN", "MISSING_INPUT", "BLOCKED", "NOT_APPLICABLE", "SYNTHETIC_ENGINEERING_ONLY"}


def assert_status(value: str) -> None:
    if value not in VALID_EVIDENCE_STATUS:
        raise ValueError(f"Invalid evidence status: {value}")

