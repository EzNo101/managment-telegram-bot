from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlencode

import httpx

from src.core.enums import PaymentMethod
from src.providers.protocol import Invoice


class StripeProvider:
    def __init__(
        self,
        api_key: str,
        webhook_secret: str,
        success_url: str,
        cancel_url: str,
        base_url: str = "https://api.stripe.com",
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        self._success_url = success_url
        self._cancel_url = cancel_url
        self._base_url = base_url.rstrip("/")
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    async def create_invoice(
        self,
        amount_usd: int,
        method: PaymentMethod,
        order_id: str,
    ) -> Invoice:
        if method != PaymentMethod.STRIPE:
            raise ValueError(f"Unsupported payment method for Stripe: {method}")

        form: dict[str, str] = {
            "mode": "payment",
            "success_url": self._success_url,
            "cancel_url": self._cancel_url,
            "client_reference_id": order_id,
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][product_data][name]": "VIP subscription",
            "line_items[0][price_data][unit_amount]": str(amount_usd),
            "line_items[0][quantity]": "1",
            "payment_method_types[0]": "card",
            "payment_method_types[1]": "paypal",
            "metadata[order_id]": order_id,
        }

        response = await self._http.post(
            url=f"{self._base_url}/v1/checkout/sessions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            content=urlencode(form),
        )
        if response.is_error:
            raise RuntimeError(
                f"Stripe checkout error {response.status_code}: {response.text}"
            )
        data = response.json()
        return Invoice(provider_ref=str(data["id"]), pay_url=data.get("url"))

    def verify_webhook(
        self,
        raw_body: bytes,
        headers: dict[str, Any],
    ) -> dict[str, Any] | None:
        signature = headers.get("stripe-signature")
        if not signature:
            return None
        params = {}
        for part in signature.split(","):
            key, _, value = part.strip().partition("=")
            params[key] = value
        timestamp = params.get("t")
        expected = params.get("v1")
        if not timestamp or not expected:
            return None
        signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}"
        computed = hmac.new(
            self._webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(computed, expected):
            return None
        return json.loads(raw_body)
