from __future__ import annotations

import asyncio
import json
import logging
from decimal import Decimal
from typing import Any

from aiohttp import ClientError, ClientSession


logger = logging.getLogger(__name__)


class PlategaApiError(RuntimeError):
    pass


class PlategaClient:
    def __init__(
        self,
        session: ClientSession,
        api_base: str,
        merchant_id: str,
        secret: str,
        *,
        create_path: str = "/transaction/process",
        create_path_fallback: str = "/v2/transaction/process",
    ) -> None:
        self._session = session
        self._api_base = api_base.rstrip("/")
        self._merchant_id = merchant_id.strip()
        self._secret = secret.strip()
        self._create_path = self._normalize_path(create_path)
        self._create_path_fallback = self._normalize_path(create_path_fallback)

    @staticmethod
    def _normalize_path(path: str) -> str:
        value = str(path or "").strip()
        if not value:
            raise ValueError("Platega API path is required")
        return value if value.startswith("/") else f"/{value}"

    def _headers(self) -> dict[str, str]:
        return {
            "X-MerchantId": self._merchant_id,
            "X-Secret": self._secret,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        primary_error: Exception | None = None
        for path in self._create_paths():
            try:
                return await self._request_with_retries("POST", path, json_payload=payload)
            except PlategaApiError as exc:
                if primary_error is None:
                    primary_error = exc
                if "404" not in str(exc) and "405" not in str(exc):
                    raise
        if primary_error is not None:
            raise primary_error
        raise PlategaApiError("Platega request failed")

    async def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        transaction_id = str(transaction_id or "").strip()
        if not transaction_id:
            raise ValueError("transaction_id is required")
        return await self._request_with_retries("GET", f"/transaction/{transaction_id}")

    def _create_paths(self) -> list[str]:
        paths = [self._create_path]
        if self._create_path_fallback and self._create_path_fallback not in paths:
            paths.append(self._create_path_fallback)
        return paths

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._api_base}{path}"
        async with self._session.request(
            method,
            url,
            params=params,
            json=json_payload,
            headers=self._headers(),
        ) as response:
            raw_text = await response.text()
            try:
                data = json.loads(raw_text) if raw_text else {}
            except json.JSONDecodeError as exc:
                raise PlategaApiError(f"Platega returned invalid JSON ({response.status})") from exc
            if response.status >= 400:
                raise PlategaApiError(self._extract_error_message(data, response.status))
            if not isinstance(data, dict):
                raise PlategaApiError("Platega returned unexpected response body")
            return data

    async def _request_with_retries(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(3):
            try:
                return await self._request(method, path, params=params, json_payload=json_payload)
            except (ClientError, asyncio.TimeoutError):
                if attempt == 2:
                    raise
                await asyncio.sleep(0.8 * (attempt + 1))
        raise PlategaApiError("Platega request failed")

    @staticmethod
    def cents_to_amount(cents: int) -> str:
        return str((Decimal(cents) / Decimal("100")).quantize(Decimal("0.01")))

    @staticmethod
    def _extract_error_message(data: Any, status_code: int) -> str:
        if isinstance(data, dict):
            for key in ("message", "error", "detail", "description", "error_description"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return f"Platega API error {status_code}: {value.strip()}"
            errors = data.get("errors")
            if isinstance(errors, list):
                joined = "; ".join(str(item).strip() for item in errors if str(item).strip())
                if joined:
                    return f"Platega API error {status_code}: {joined}"
        if isinstance(data, str) and data.strip():
            return f"Platega API error {status_code}: {data.strip()}"
        logger.error("Unexpected Platega error payload: %s", data)
        return f"Platega API error {status_code}"
