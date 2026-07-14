"""Application configuration from environment."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEBUG: bool = _env_bool("DEBUG")

# Rate limiting (inbound API + outbound MakerWorld fetches)
RATE_LIMIT_ENABLED: bool = _env_bool("RATE_LIMIT_ENABLED", default=True)
RATE_LIMIT_IMPORT_PER_MINUTE: int = _env_int("RATE_LIMIT_IMPORT_PER_MINUTE", 12)
RATE_LIMIT_OUTBOUND_MIN_INTERVAL: float = _env_float(
    "RATE_LIMIT_OUTBOUND_MIN_INTERVAL", 1.0
)
RATE_LIMIT_MAX_CONCURRENT_SCRAPES: int = _env_int("RATE_LIMIT_MAX_CONCURRENT_SCRAPES", 2)
RATE_LIMIT_SYNC_PRICING_PER_MINUTE: int = _env_int("RATE_LIMIT_SYNC_PRICING_PER_MINUTE", 10)
SYNC_PRICING_MAX_PARTS: int = _env_int("SYNC_PRICING_MAX_PARTS", 200)

# McMaster Product Information API (optional — B2B credentials required)
MCMASTER_API_ENABLED: bool = _env_bool("MCMASTER_API_ENABLED", default=False)
MCMASTER_API_BASE_URL: str = os.getenv(
    "MCMASTER_API_BASE_URL", "https://api.mcmaster.com/v1"
).strip()
MCMASTER_API_USERNAME: str = os.getenv("MCMASTER_API_USERNAME", "").strip()
MCMASTER_API_PASSWORD: str = os.getenv("MCMASTER_API_PASSWORD", "").strip()
MCMASTER_API_CERT_PATH: str = os.getenv("MCMASTER_API_CERT_PATH", "").strip()

# McMaster public-site matching (offline filter URLs + optional live browse)
MCMASTER_FILTERED_BROWSE_ENABLED: bool = _env_bool(
    "MCMASTER_FILTERED_BROWSE_ENABLED", default=True
)
MCMASTER_BROWSE_RESOLVE_ENABLED: bool = _env_bool(
    "MCMASTER_BROWSE_RESOLVE_ENABLED", default=False
)

# Match-error report dispatch (optional — email, GitHub issues, webhooks)
FEEDBACK_DISPATCH_ENABLED: bool = _env_bool("FEEDBACK_DISPATCH_ENABLED", default=False)

FEEDBACK_EMAIL_ENABLED: bool = _env_bool("FEEDBACK_EMAIL_ENABLED", default=False)
FEEDBACK_SMTP_HOST: str = os.getenv("FEEDBACK_SMTP_HOST", "").strip()
FEEDBACK_SMTP_PORT: int = _env_int("FEEDBACK_SMTP_PORT", 587)
FEEDBACK_SMTP_USER: str = os.getenv("FEEDBACK_SMTP_USER", "").strip()
FEEDBACK_SMTP_PASSWORD: str = os.getenv("FEEDBACK_SMTP_PASSWORD", "").strip()
FEEDBACK_SMTP_FROM: str = os.getenv("FEEDBACK_SMTP_FROM", "").strip()
FEEDBACK_SMTP_USE_TLS: bool = _env_bool("FEEDBACK_SMTP_USE_TLS", default=True)
FEEDBACK_EMAIL_TO: str = os.getenv("FEEDBACK_EMAIL_TO", "").strip()

FEEDBACK_GITHUB_ENABLED: bool = _env_bool("FEEDBACK_GITHUB_ENABLED", default=False)
FEEDBACK_GITHUB_TOKEN: str = os.getenv("FEEDBACK_GITHUB_TOKEN", "").strip()
FEEDBACK_GITHUB_REPO: str = os.getenv("FEEDBACK_GITHUB_REPO", "").strip()
FEEDBACK_GITHUB_LABELS: str = os.getenv(
    "FEEDBACK_GITHUB_LABELS", "bug,match-report"
).strip()

FEEDBACK_WEBHOOK_ENABLED: bool = _env_bool("FEEDBACK_WEBHOOK_ENABLED", default=False)
FEEDBACK_WEBHOOK_URLS: str = os.getenv("FEEDBACK_WEBHOOK_URLS", "").strip()
FEEDBACK_WEBHOOK_TIMEOUT: float = _env_float("FEEDBACK_WEBHOOK_TIMEOUT", 15.0)
