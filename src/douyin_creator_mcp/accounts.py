"""Account identifiers and isolated browser profile paths."""

from __future__ import annotations

import re
from pathlib import Path

from .errors import VALIDATION_ERROR, AppError


BROWSER_DEFAULT_ACCOUNT_ID = "browser-default"
_ACCOUNT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_account_id(account_id: str) -> str:
    normalized = str(account_id or "").strip()
    if not _ACCOUNT_ID.fullmatch(normalized):
        raise AppError(
            VALIDATION_ERROR,
            "account_id must be 1-64 characters using letters, digits, dot, underscore, or hyphen.",
        )
    return normalized


def browser_profile_dir(
    legacy_profile_dir: Path,
    profiles_root: Path,
    account_id: str,
) -> Path:
    """Keep the legacy default profile while isolating every named account."""
    normalized = validate_account_id(account_id)
    if normalized == BROWSER_DEFAULT_ACCOUNT_ID:
        return legacy_profile_dir
    return profiles_root / normalized
