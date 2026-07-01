"""Shared helpers for security and repository hygiene tests."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# Values injected during API leak tests — must not appear in responses.
LEAK_BAIT = {
    "username": "leak-bait-mcmaster-user-xyzzy",
    "password": "leak-bait-mcmaster-pass-plugh",
    "cert_path": "/home/leak/bait-cert-plugh.pfx",
}

# Patterns that must not appear in committed source (excluding this module's bait strings).
TRACKED_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"), "private key block"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"), "GitHub personal access token"),
    (re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"), "API secret key (sk-…)"),
    (
        re.compile(r"(?i)(?:api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
        "hardcoded credential assignment",
    ),
]

TRACKED_FILE_SUFFIXES = {
    ".py",
    ".json",
    ".md",
    ".toml",
    ".yml",
    ".yaml",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".ipynb",
    ".sh",
    ".env",
}

SKIP_TRACKED_PATH_PREFIXES = (
    "tests/guardrails.py",
    "tests/test_guardrails.py",
)


def git_tracked_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8")
        if rel.startswith(SKIP_TRACKED_PATH_PREFIXES):
            continue
        paths.append(repo_root / rel)
    return paths


def assert_no_leak_bait(text: str) -> None:
    for label, value in LEAK_BAIT.items():
        assert value not in text, f"response leaked leak-bait {label}"


def scan_text_for_secret_patterns(text: str, *, path: str) -> list[str]:
    hits: list[str] = []
    for pattern, label in TRACKED_SECRET_PATTERNS:
        if any(bait in text for bait in LEAK_BAIT.values()):
            continue
        if pattern.search(text):
            hits.append(f"{path}: possible {label}")
    return hits
