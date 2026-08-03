from dataclasses import dataclass
from typing import Any, Protocol

from src.core.enums import PaymentMethod


@dataclass
class Invoice:
    """Represents an invoice created by a payment provider."""

    provider_ref: str
    pay_url: str | None = None
    pay_address: str | None = None


class PaymentProvider(Protocol):
    """Protocol for payment providers."""

    async def create_invoice(
        self,
        amount_usd: int,
        method: PaymentMethod,
    ) -> Invoice:
        """Create an invoice for a user and plan."""
        ...

    def verify_webhook(self, payload: dict[str, Any], headers: dict[str, Any]) -> bool:
        """Verify the authenticity of a webhook request."""
        ...
