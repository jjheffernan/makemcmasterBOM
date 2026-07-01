"""McMaster-Carr Product Information API client (optional B2B integration).

Official docs: https://www.mcmaster.com/help/api/
Base URL: https://api.mcmaster.com/v1

Approved customers receive a PFX client certificate + account credentials.
Contact eprocurement@mcmaster.com to enable access.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from backend import config
from backend.services.vendors.mcmaster.urls import MCMASTER_API_BASE, mcmaster_product_url

logger = logging.getLogger(__name__)


@dataclass
class McMasterApiError(Exception):
    error_code: int
    error_message: str
    error_description: str = ""

    def __str__(self) -> str:
        return f"{self.error_message}: {self.error_description}"


@dataclass(frozen=True)
class McMasterSpecification:
    attribute: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class McMasterProductRecord:
    part_number: str
    product_status: str
    family_description: str
    detail_description: str
    specifications: tuple[McMasterSpecification, ...] = ()
    links: dict[str, str] = field(default_factory=dict)
    suggested_product_url: str = ""
    suggested_product_differences: tuple[dict[str, str], ...] = ()

    @property
    def is_discontinued(self) -> bool:
        return self.product_status.lower() in {"discontinued", "inactive"}

    @property
    def catalog_url(self) -> str:
        return mcmaster_product_url(self.part_number)


def _parse_specifications(raw: list[dict[str, Any]]) -> tuple[McMasterSpecification, ...]:
    specs: list[McMasterSpecification] = []
    for item in raw:
        attribute = str(item.get("Attribute", "")).strip()
        values = tuple(str(v) for v in item.get("Values", []) if str(v).strip())
        if attribute:
            specs.append(McMasterSpecification(attribute=attribute, values=values))
    return tuple(specs)


def _parse_links(raw: list[dict[str, Any]]) -> dict[str, str]:
    links: dict[str, str] = {}
    for item in raw:
        key = str(item.get("Key", "")).strip()
        value = str(item.get("Value", "")).strip()
        if key and value:
            links[key] = value
    return links


def parse_product_payload(payload: dict[str, Any]) -> McMasterProductRecord:
    part_number = str(payload.get("PartNumber", "")).strip()
    differences = tuple(
        {
            "attribute": str(item.get("Attribute", "")),
            "discontinued": str(item.get("DiscontinuedProductValue", "")),
            "suggested": str(item.get("SuggestedProductValue", "")),
        }
        for item in payload.get("SuggestedProductDifferences", [])
    )
    suggested = ""
    for key, value in _parse_links(payload.get("Links", [])).items():
        if key == "SuggestedProduct":
            suggested = value
            break
    return McMasterProductRecord(
        part_number=part_number,
        product_status=str(payload.get("ProductStatus", "")),
        family_description=str(payload.get("FamilyDescription", "")),
        detail_description=str(payload.get("DetailDescription", "")),
        specifications=_parse_specifications(payload.get("Specifications", [])),
        links=_parse_links(payload.get("Links", [])),
        suggested_product_url=suggested,
        suggested_product_differences=differences,
    )


class McMasterApiClient:
    """Thin async wrapper around McMaster's REST API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        cert_path: str | None = None,
    ) -> None:
        self.base_url = (base_url or config.MCMASTER_API_BASE_URL or MCMASTER_API_BASE).rstrip("/")
        self.username = username or config.MCMASTER_API_USERNAME
        self.password = password or config.MCMASTER_API_PASSWORD
        self.cert_path = cert_path or config.MCMASTER_API_CERT_PATH
        self._token: str | None = None
        self._token_expires: datetime | None = None

    def is_configured(self) -> bool:
        return bool(
            config.MCMASTER_API_ENABLED
            and self.username
            and self.password
            and self.cert_path
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(cert=self.cert_path, timeout=30.0)

    def _auth_headers(self) -> dict[str, str]:
        if not self._token:
            raise RuntimeError("McMaster API is not logged in")
        return {"Authorization": f"Bearer {self._token}"}

    async def _raise_api_error(self, response: httpx.Response) -> None:
        try:
            payload = response.json()
        except Exception:
            response.raise_for_status()
            return
        if isinstance(payload, dict) and "ErrorMessage" in payload:
            raise McMasterApiError(
                error_code=int(payload.get("ErrorCode", response.status_code)),
                error_message=str(payload.get("ErrorMessage", "")),
                error_description=str(payload.get("ErrorDescription", "")),
            )
        response.raise_for_status()

    async def login(self) -> str:
        if not self.is_configured():
            raise RuntimeError("McMaster API is not configured")

        async with self._client() as client:
            response = await client.post(
                f"{self.base_url}/login",
                json={"UserName": self.username, "Password": self.password},
            )
            await self._raise_api_error(response)
            payload = response.json()
            token = payload.get("AuthToken") or payload.get("authToken")
            if not token:
                raise RuntimeError("McMaster API login response missing AuthToken")
            self._token = str(token)
            expiration = payload.get("ExpirationTS")
            if expiration:
                try:
                    self._token_expires = datetime.fromisoformat(
                        str(expiration).replace("Z", "+00:00")
                    )
                except ValueError:
                    self._token_expires = None
            return self._token

    async def logout(self) -> None:
        if not self._token:
            return
        async with self._client() as client:
            response = await client.post(
                f"{self.base_url}/logout",
                headers=self._auth_headers(),
            )
            if response.status_code not in {204, 200}:
                await self._raise_api_error(response)
        self._token = None
        self._token_expires = None

    async def _ensure_token(self) -> None:
        if not self._token:
            await self.login()
            return
        if self._token_expires and datetime.now(timezone.utc) >= self._token_expires:
            await self.login()

    async def add_product(self, part_number: str) -> McMasterProductRecord:
        """Subscribe to a part and return product metadata (PUT /v1/products)."""
        await self._ensure_token()
        async with self._client() as client:
            response = await client.put(
                f"{self.base_url}/products",
                headers=self._auth_headers(),
                json={"URL": f"https://mcmaster.com/{part_number}"},
            )
            await self._raise_api_error(response)
            return parse_product_payload(response.json())

    async def fetch_product(self, part_number: str) -> McMasterProductRecord | None:
        """GET /v1/products/{partNumber} — requires prior subscription."""
        if not self.is_configured():
            return None
        await self._ensure_token()
        async with self._client() as client:
            response = await client.get(
                f"{self.base_url}/products/{part_number}",
                headers=self._auth_headers(),
            )
            if response.status_code == 404:
                return None
            await self._raise_api_error(response)
            return parse_product_payload(response.json())

    async def lookup_product(self, part_number: str) -> McMasterProductRecord | None:
        """Add (subscribe) then fetch — convenience for one-off enrichment."""
        if not self.is_configured():
            return None
        try:
            return await self.add_product(part_number)
        except McMasterApiError as exc:
            if exc.error_message == "NOT_SUBSCRIBED_TO_PRODUCT":
                return await self.fetch_product(part_number)
            if "Invalid part number" in exc.error_description:
                return None
            raise

    async def fetch_price(self, part_number: str) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        await self._ensure_token()
        async with self._client() as client:
            response = await client.get(
                f"{self.base_url}/products/{part_number}/price",
                headers=self._auth_headers(),
            )
            if response.status_code == 404:
                return []
            await self._raise_api_error(response)
            payload = response.json()
            return payload if isinstance(payload, list) else []


_default_client: McMasterApiClient | None = None


def get_mcmaster_api_client() -> McMasterApiClient:
    global _default_client
    if _default_client is None:
        _default_client = McMasterApiClient()
    return _default_client
