"""Security guardrails — no credential leaks in API responses or tracked files."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from backend import config
from backend.api import store
from backend.main import debug_exception_handler
from backend.models.project import Project
from tests.conftest import REPO_ROOT
from tests.guardrails import (
    LEAK_BAIT,
    TRACKED_FILE_SUFFIXES,
    assert_no_leak_bait,
    git_tracked_files,
    scan_text_for_secret_patterns,
)


@pytest.fixture
def leak_bait_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate configured McMaster API credentials (worst-case leak surface)."""
    monkeypatch.setattr(config, "MCMASTER_API_USERNAME", LEAK_BAIT["username"])
    monkeypatch.setattr(config, "MCMASTER_API_PASSWORD", LEAK_BAIT["password"])
    monkeypatch.setattr(config, "MCMASTER_API_CERT_PATH", LEAK_BAIT["cert_path"])
    monkeypatch.setattr(config, "FEEDBACK_GITHUB_TOKEN", LEAK_BAIT["github_token"])
    monkeypatch.setattr(config, "FEEDBACK_SMTP_PASSWORD", LEAK_BAIT["smtp_password"])
    monkeypatch.setattr(config, "DEBUG", True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("GET", "/api/health", {}),
        ("GET", "/api/debug", {}),
        ("GET", "/api/notebooks", {}),
        ("GET", "/api/import/stages", {}),
        ("GET", "/api/bom/history", {}),
    ],
)
async def test_api_responses_do_not_leak_credentials(
    api_client: AsyncClient,
    leak_bait_env: None,
    method: str,
    path: str,
    kwargs: dict,
) -> None:
    response = await api_client.request(method, path, **kwargs)
    assert response.status_code == 200
    assert_no_leak_bait(response.text)


@pytest.mark.asyncio
async def test_import_file_response_does_not_leak_credentials(
    api_client: AsyncClient,
    leak_bait_env: None,
) -> None:
    csv_content = b"Qty,Part Name,Specification\n2,M3 bolt,Stainless\n"
    response = await api_client.post(
        "/api/import/file",
        files={"file": ("bom.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    assert_no_leak_bait(response.text)


@pytest.mark.asyncio
async def test_bom_get_response_does_not_leak_credentials(
    api_client: AsyncClient,
    leak_bait_env: None,
) -> None:
    project_id = store.save(Project(title="Guardrail", parts=[]))
    response = await api_client.get(f"/api/bom/{project_id}")
    assert response.status_code == 200
    assert_no_leak_bait(response.text)


@pytest.mark.asyncio
async def test_feedback_response_does_not_leak_credentials(
    api_client: AsyncClient,
    leak_bait_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("MATCH_REPORTS_PATH", str(tmp_path / "reports.jsonl"))
    monkeypatch.setattr(config, "FEEDBACK_DISPATCH_ENABLED", True)
    monkeypatch.setattr(config, "FEEDBACK_GITHUB_ENABLED", True)
    monkeypatch.setattr(config, "FEEDBACK_GITHUB_REPO", "owner/repo")
    monkeypatch.setattr(config, "FEEDBACK_EMAIL_ENABLED", False)
    monkeypatch.setattr(config, "FEEDBACK_WEBHOOK_ENABLED", False)

    response = await api_client.post(
        "/api/feedback/match-error",
        json={
            "issue_type": "other",
            "message": "Guardrail feedback leak test",
        },
    )
    assert response.status_code == 200
    assert_no_leak_bait(response.text)


@pytest.mark.asyncio
async def test_global_exception_handler_hides_traceback_when_debug_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "DEBUG", False)
    request = MagicMock()
    request.url.path = "/api/test"

    response = await debug_exception_handler(
        request,
        RuntimeError("traceback-should-not-appear-xyzzy"),
    )
    payload = json.loads(response.body)
    assert payload["detail"] == "Internal server error"
    assert "traceback" not in payload
    assert "traceback-should-not-appear" not in json.dumps(payload)


@pytest.mark.asyncio
async def test_health_never_exposes_credential_config(
    api_client: AsyncClient,
    leak_bait_env: None,
) -> None:
    response = await api_client.get("/api/health")
    body = response.json()
    assert "mcmaster" not in json.dumps(body).lower()
    assert_no_leak_bait(response.text)


@pytest.mark.asyncio
async def test_debug_proxy_env_redacts_credentials(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy-user:proxy-secret-pass@proxy.example:8080")
    response = await api_client.get("/api/debug")
    assert response.status_code == 200
    body = response.text
    assert "proxy-secret-pass" not in body
    assert "proxy-user" not in body
    assert "proxy.example" in body


def test_tracked_files_do_not_include_env() -> None:
    result = subprocess.run(
        ["git", "ls-files", ".env", ".env.*"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked == [], f".env files must not be committed: {tracked}"


def test_tracked_source_has_no_obvious_secrets() -> None:
    violations: list[str] = []
    for path in git_tracked_files(REPO_ROOT):
        if path.suffix not in TRACKED_FILE_SUFFIXES and path.name != ".env":
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        violations.extend(scan_text_for_secret_patterns(text, path=rel))

    assert not violations, "Possible secrets in tracked files:\n" + "\n".join(violations)
