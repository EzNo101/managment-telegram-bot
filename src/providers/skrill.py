from __future__ import annotations

import hashlib
import hmac
from typing import Any
from urllib.parse import urlencode

from src.core.enums import PaymentMethod
from src.providers.protocol import Invoice


class SkrillProvider:
    def __init__(
        self,
        pay_to_email: str,
        merchant_id: str,
        secret_word: str,
        status_url: str,
        return_url: str,
        cancel_url: str,
        base_url: str = "https://pay.skrill.com",
    ) -> None:
        self._pay_to_email = pay_to_email
        self._merchant_id = merchant_id
        self._secret_word = secret_word
        self._status_url = status_url
        self._return_url = return_url
        self._cancel_url = cancel_url
        self._base_url = base_url.rstrip("/")

    async def create_invoice(
        self,
        amount_usd: int,
        method: PaymentMethod,
        order_id: str,
    ) -> Invoice:
        if method != PaymentMethod.SKRILL:
            raise ValueError(f"Unsupported payment method for Skrill: {method}")

        params: dict[str, str] = {
            "pay_to_email": self._pay_to_email,
            "recipient_description": "Management Bot",
            "transaction_id": order_id,
            "amount": f"{amount_usd / 100:.2f}",
            "currency": "USD",
            "detail1_description": "VIP subscription",
            "status_url": self._status_url,
            "return_url": self._return_url,
            "cancel_url": self._cancel_url,
            "language": "EN",
        }
        return Invoice(
            provider_ref=order_id,
            pay_url=f"{self._base_url}/?{urlencode(params)}",
        )

    def verify_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any],
    ) -> bool:
        received = payload.get("md5sig")
        required = (
            payload.get("merchant_id"),
            payload.get("transaction_id"),
            payload.get("mb_amount"),
            payload.get("mb_currency"),
            payload.get("status"),
        )
        if not received or not all(required):
            return False

        secret_md5 = hashlib.md5(self._secret_word.encode()).hexdigest().upper()
        to_hash = "".join(required[:2])
        to_hash += secret_md5
        to_hash += "".join(required[2:])
        computed = hashlib.md5(to_hash.encode()).hexdigest().upper()

        return hmac.compare_digest(computed, received)
