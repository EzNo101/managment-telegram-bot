from enum import StrEnum


class PaymentMethod(StrEnum):
    BITCOIN = "bitcoin"
    USDT = "usdt"
    SKRILL = "skrill"
    PAYPAL = "paypal"
    GOOGLE_PAY = "google_pay"
    NETELLER = "neteller"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    FAILED = "failed"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
