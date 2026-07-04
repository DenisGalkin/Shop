from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
from decimal import Decimal
from typing import Any

from aiohttp import ClientError, ClientSession


logger = logging.getLogger(__name__)


class HeleketApiError(RuntimeError):
    pass


class HeleketClient:
    def __init__(self, session: ClientSession, api_base: str, merchant_uuid: str, api_key: str) -> None:
        self._session = session
        self._api_base = api_base.rstrip("/")
        self._merchant_uuid = merchant_uuid.strip()
        self._api_key = api_key.strip()

    async def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request_with_retries("/v1/payment", payload)
        invoice = response.get("result")
        if not isinstance(invoice, dict):
            raise HeleketApiError("Heleket did not return invoice payload")
        return invoice

    async def get_payment(self, *, uuid: str | None = None, order_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if uuid:
            payload["uuid"] = uuid
        if order_id:
            payload["order_id"] = order_id
        if not payload:
            raise ValueError("uuid or order_id is required")
        response = await self._request_with_retries("/v1/payment/info", payload)
        payment = response.get("result")
        if not isinstance(payment, dict):
            raise HeleketApiError("Heleket did not return payment payload")
        return payment

    def sign_webhook_payload(self, payload: dict[str, Any]) -> str:
        encoded = self._canonical_json_bytes(payload)
        digest_input = base64.b64encode(encoded).decode("ascii") + self._api_key
        return hashlib.md5(digest_input.encode("utf-8")).hexdigest()

    async def _request_with_retries(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            try:
                return await self._request(path, payload)
            except (ClientError, asyncio.TimeoutError):
                if attempt == 2:
                    raise
                await asyncio.sleep(0.8 * (attempt + 1))
        raise HeleketApiError("Heleket request failed")

    async def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = self._canonical_json_bytes(payload)
        url = f"{self._api_base}{path}"
        async with self._session.post(
            url,
            data=body,
            headers=self._headers(body),
        ) as response:
            raw_text = await response.text()
            try:
                data = json.loads(raw_text) if raw_text else {}
            except json.JSONDecodeError as exc:
                raise HeleketApiError(f"Heleket returned invalid JSON ({response.status})") from exc
            if response.status >= 400:
                raise HeleketApiError(self._extract_error_message(data, response.status))
            if not isinstance(data, dict):
                raise HeleketApiError("Heleket returned unexpected response body")
            state = data.get("state")
            if state not in (0, "0", None):
                raise HeleketApiError(self._extract_error_message(data, response.status))
            return data

    def _headers(self, body: bytes) -> dict[str, str]:
        digest_input = base64.b64encode(body).decode("ascii") + self._api_key
        sign = hashlib.md5(digest_input.encode("utf-8")).hexdigest()
        return {
            "merchant": self._merchant_uuid,
            "sign": sign,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def cents_to_amount(cents: int) -> str:
        return str((Decimal(cents) / Decimal("100")).quantize(Decimal("0.01")))

    @staticmethod
    def _extract_error_message(data: Any, status_code: int) -> str:
        if isinstance(data, dict):
            for key in ("message", "error", "detail", "description", "error_description"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return f"Heleket API error {status_code}: {value.strip()}"
            errors = data.get("errors")
            if isinstance(errors, list):
                joined = "; ".join(str(item).strip() for item in errors if str(item).strip())
                if joined:
                    return f"Heleket API error {status_code}: {joined}"
        if isinstance(data, str) and data.strip():
            return f"Heleket API error {status_code}: {data.strip()}"
        logger.error("Unexpected Heleket error payload: %s", data)
        return f"Heleket API error {status_code}"
