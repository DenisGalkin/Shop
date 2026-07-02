from __future__ import annotations

import asyncio
import json
import logging
from decimal import Decimal
from typing import Any

from aiohttp import ClientError, ClientSession


logger = logging.getLogger(__name__)


class CryptoBotApiError(RuntimeError):
    pass


class CryptoBotClient:
    def __init__(self, session: ClientSession, api_base: str, api_token: str) -> None:
        self._session = session
        self._api_base = api_base.rstrip("/")
        self._api_token = api_token

    def _headers(self) -> dict[str, str]:
        return {
            "Crypto-Pay-API-Token": self._api_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request_with_retries("POST", "/createInvoice", json_payload=payload)
        invoice = response.get("result")
        if not isinstance(invoice, dict):
            raise CryptoBotApiError("Crypto Pay did not return invoice payload")
        return invoice

    async def get_invoices(self, *, invoice_ids: list[int] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if invoice_ids:
            params["invoice_ids"] = ",".join(str(invoice_id) for invoice_id in invoice_ids)
        response = await self._request_with_retries("GET", "/getInvoices", params=params)
        invoices = response.get("result", {}).get("items")
        if not isinstance(invoices, list):
            raise CryptoBotApiError("Crypto Pay did not return invoices list")
        return [invoice for invoice in invoices if isinstance(invoice, dict)]

    async def get_invoice(self, *, invoice_id: int) -> dict[str, Any]:
        invoices = await self.get_invoices(invoice_ids=[invoice_id])
        for invoice in invoices:
            if int(invoice.get("invoice_id", 0)) == invoice_id:
                return invoice
        raise CryptoBotApiError("Crypto Pay invoice not found")

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
                raise CryptoBotApiError(f"Crypto Pay returned invalid JSON ({response.status})") from exc
            if response.status >= 400:
                raise CryptoBotApiError(self._extract_error_message(data, response.status))
            if not isinstance(data, dict):
                raise CryptoBotApiError("Crypto Pay returned unexpected response body")
            if not data.get("ok", False):
                raise CryptoBotApiError(self._extract_error_message(data, response.status))
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
        raise CryptoBotApiError("Crypto Pay request failed")

    @staticmethod
    def cents_to_amount(cents: int) -> str:
        return str((Decimal(cents) / Decimal("100")).quantize(Decimal("0.01")))

    @staticmethod
    def _extract_error_message(data: dict[str, Any], status_code: int) -> str:
        error = data.get("error")
        if isinstance(error, dict):
            detail = error.get("name") or error.get("code") or error.get("message")
            if detail:
                return f"Crypto Pay API error {status_code}: {detail}"
        if isinstance(error, str) and error:
            return f"Crypto Pay API error {status_code}: {error}"
        logger.error("Unexpected Crypto Pay error payload: %s", data)
        return f"Crypto Pay API error {status_code}"
