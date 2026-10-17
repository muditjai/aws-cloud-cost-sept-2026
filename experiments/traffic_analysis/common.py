"""Configuration, safe output, and small shared data transformations."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.parse import urlsplit

from dotenv import dotenv_values

Result = TypeVar("Result")
Json = dict[str, Any]


def load_environment(path: Path) -> dict[str, str]:
    """The explicitly selected dotenv file wins, without expanding secret values."""
    values = dict(os.environ)
    if path.exists():
        values.update({name: value for name, value in dotenv_values(path, interpolate=False).items()
                       if value is not None})
    return values


class Redactor:
    def __init__(self, environment: dict[str, str]) -> None:
        self.secrets = sorted({value for name, value in environment.items()
                               if re.search(r"TOKEN|PAT$|SECRET|PASSWORD|API_KEY|ACCESS_KEY", name)
                               and len(value) >= 8}, key=len, reverse=True)

    def clean(self, text: str) -> str:
        for secret in self.secrets:
            text = text.replace(secret, "[REDACTED]")
        text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
                      "[REDACTED PRIVATE KEY]", text, flags=re.S)
        text = re.sub(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9_]{20,}"
                      r"|\bgithub_pat_[A-Za-z0-9_]+|\bsk-[A-Za-z0-9_-]{16,}", "[REDACTED]", text)
        text = re.sub(r"(?i)((?:password|secret|token|api[_-]?key|authorization|access[_-]?key)"
                      r"[\w-]*[\"']?\s*[:=]\s*)[\"'][^\"'\n]+[\"']",
                      r'\1"[REDACTED]"', text)
        text = re.sub(r"(https?://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", text)
        # Signed URLs, user IDs, and query strings do not belong in evidence snippets.
        return re.sub(r"(https?://[^\s\"'<>?\\]+)\?[^\s\"'<>\\]*", r"\1?[REDACTED]", text)


def safe_error(error: Exception) -> str:
    """Do not log response bodies, signed URLs, or credential-bearing exceptions."""
    response = getattr(error, "response", None)
    if isinstance(response, dict):
        return str(response.get("Error", {}).get("Code", type(error).__name__))
    status = getattr(response, "status_code", None)
    return f"{type(error).__name__}" + (f" (HTTP {status})" if status else "")


def attempt(issues: list[str], label: str, call: Callable[[], Result], fallback: Result) -> Result:
    """Collection boundary: preserve partial evidence and explicitly record missing data."""
    from botocore.exceptions import BotoCoreError, ClientError
    from requests import RequestException

    try:
        return call()
    except (BotoCoreError, ClientError, RequestException, OSError, ValueError) as error:
        issues.append(f"{label}: {safe_error(error)}")
        return fallback


def write_private(path: Path, payload: str, redactor: Redactor) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(redactor.clean(payload))
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def save_json(path: Path, evidence: Json, redactor: Redactor) -> None:
    write_private(path, json.dumps(evidence, indent=2, default=str), redactor)


def utc_day(value: date) -> datetime:
    return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)


def normalize_host(value: str) -> str:
    host = value.lower().rstrip(".")
    return host.removeprefix("dualstack.")


def route_key(request: str) -> tuple[str, str, str]:
    """Drop query strings and coarsen object IDs before keeping any access-log data."""
    parts = request.split()
    if len(parts) < 2:
        raise ValueError("Missing HTTP request")
    parsed = urlsplit(parts[1])
    path = re.sub(r"[\r\n\t]", "", parsed.path)[:300]
    path = re.sub(r"(?<=/)(?:\d+|[0-9a-fA-F-]{16,})(?=/|\.|$)", "{id}", path)
    path = re.sub(r"(?<=/)[^/]*@[^/]*(?=/|$)", "{redacted}", path)
    return parts[0], normalize_host(parsed.hostname or "unknown"), path or "/"
