from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str

    # Database
    DB_URL: str
    DB_POOL_SIZE: int
    DB_POOL_RECYCLE: int
    DB_POOL_TIMEOUT: int
    DB_PRE_PING: bool

    # Basic admins
    ADMIN_IDS: list[int]

    # NOWPayments
    NOWPAYMENTS_API_KEY: str
    NOWPAYMENTS_IPN_SECRET: str
    NOWPAYMENTS_WEBHOOK_URL: str

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_WEBHOOK_URL: str = ""
    STRIPE_SUCCESS_URL: str = ""
    STRIPE_CANCEL_URL: str = ""

    # Private channel
    CHANNEL_ID: int
    INVITE_EXPIRE_SECONDS: int = 3 * 24 * 3600

    # Workers
    REMIND_DAYS_BEFORE: int = 3
    STALE_PAYMENT_TTL_HOURS: int = 48

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore
