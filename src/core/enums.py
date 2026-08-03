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
    REFUNDED = "refunded"
    FAILED = "failed"
    EXPIRED = "expired"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
