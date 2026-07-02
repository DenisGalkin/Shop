from __future__ import annotations

import asyncio
import json
import logging
from decimal import Decimal
from typing import Any

from aiohttp import ClientError, ClientSession


logger = logging.getLogger(__name__)


class LolzteamApiError(RuntimeError):
    pass


class LolzteamClient:
    def __init__(self, session: ClientSession, api_base: str, api_token: str) -> None:
        self._session = session
        self._api_base = api_base.rstrip("/")
        self._api_token = api_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request_with_retries("POST", "/invoice", json_payload=payload)
        return self._extract_invoice(response)

    async def get_invoice(
        self,
        *,
        invoice_id: int | None = None,
        payment_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if invoice_id is not None:
            params["invoice_id"] = invoice_id
        if payment_id:
            params["payment_id"] = payment_id
        if not params:
            raise ValueError("invoice_id or payment_id is required")
        response = await self._request_with_retries("GET", "/invoice", params=params)
        return self._extract_invoice(response)

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
                raise LolzteamApiError(f"Lolzteam returned invalid JSON ({response.status})") from exc
            if response.status >= 400:
                raise LolzteamApiError(self._extract_error_message(data, response.status))
            if not isinstance(data, dict):
                raise LolzteamApiError("Lolzteam returned unexpected response body")
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
        raise LolzteamApiError("Lolzteam request failed")

    @staticmethod
    def cents_to_amount(cents: int) -> str:
        return str((Decimal(cents) / Decimal("100")).quantize(Decimal("0.01")))

    @staticmethod
    def _extract_invoice(data: dict[str, Any]) -> dict[str, Any]:
        invoice = data.get("invoice", data)
        if not isinstance(invoice, dict):
            raise LolzteamApiError("Lolzteam did not return invoice payload")
        return invoice

    @staticmethod
    def _extract_error_message(data: Any, status_code: int) -> str:
        if isinstance(data, dict):
            for key in ("error_description", "description", "detail", "message", "error"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return f"Lolzteam API error {status_code}: {value.strip()}"
        if isinstance(data, str) and data.strip():
            return f"Lolzteam API error {status_code}: {data.strip()}"
        logger.error("Unexpected Lolzteam error payload: %s", data)
        return f"Lolzteam API error {status_code}"
