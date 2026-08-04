from __future__ import annotations

import hashlib  # SHA-512
import hmac
import json
from typing import Any

import httpx

from src.core.enums import PaymentMethod
from src.providers.protocol import Invoice


class NowPaymentsProvider:
    def __init__(
        self,
        api_key: str,
        ipn_secret: str,
        ipn_callback_url: str,
        base_url: str = "https://api.nowpayments.io",
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._ipn_secret = ipn_secret
        self._ipn_callback_url = ipn_callback_url
        self._base_url = base_url.rstrip("/")
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    def _coins(self, payment_method: PaymentMethod) -> str:
        if payment_method == PaymentMethod.BITCOIN:
            return "btc"
        elif payment_method == PaymentMethod.USDT:
            return "usdttrc20"
        else:
            raise ValueError(f"Unsupported payment method: {payment_method}")

    async def create_invoice(
        self,
        usd_amount: int,
        payment_method: PaymentMethod,
    ) -> Invoice:
        payload: dict[str, Any] = {
            "price_amount": usd_amount / 100,  # Convert cents to dollars
            "price_currency": "usd",
            "pay_currency": self._coins(payment_method),
            "ipn_callback_url": self._ipn_callback_url,
        }
        response = await self._http.post(
            url=f"{self._base_url}/v1/invoice",
            headers={"x-api-key": self._api_key, "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("status", True):
            raise RuntimeError(f"NOWPayments error: {data.get('message')}")
        return Invoice(provider_ref=str(data["id"]), pay_url=data.get("invoice_url"))

    def verify_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any],
    ) -> bool:
        received = headers.get("x-nowpayments-sig")
        if not received:
            return False

        sorted_msg = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        computed = hmac.new(
            self._ipn_secret.encode(),
            sorted_msg.encode(),
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(computed, received)
