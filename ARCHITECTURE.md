# Архітектура: Telegram VIP-канал бот

> Документ для орієнтування під час кодингу. Містить огляд системи, моделі даних,
> шари, платіжну абстракцію, ключові потоки та план робіт.

---

## 1. Огляд системи

Один процес: aiogram-бот + aiohttp-вебхук-сервер. Postgres — єдине джерело істини.
Фонові задачі — APScheduler.

```
┌──────────────── Telegram user ────────────────┐
│ /plans → plan → method → платіж → invite-link │
└──────────────────────┬───────────────────────┘
                       │
        ┌──────────────┴───────────────┐
        │         app (1 процес)        │
        │  aiogram router/FSM          │
        │  application (use cases)     │
        │  infra/db (репозиторії)      │
        │  APScheduler (фонові задачі) │
        └──────┬──────────────┬────────┘
               │              │
     ┌─────────┴──┐   ┌───────┴────────┐
     │  Postgres  │   │  платіжні PSP  │
     └────────────┘   │  + blockchain  │
                      └────────────────┘
```

Режими роботи:
- **Webhook** — потрібен `PUBLIC_URL` (HTTPS). Telegram webhook монтується на
  `PUBLIC_URL/webhook/telegram`, платіжні — на `POST /webhook/{method}`.
- **Polling** — `PUBLIC_URL` пустий (локальний дев).

---

## 2. Моделі даних

### users

| поле | тип | опис |
|---|---|---|
| id | PK | |
| telegram_id | BIGINT unique | |
| username / first_name | str? | |
| is_admin | bool | |
| created_at / updated_at | tz timestamp | |

### plans

| поле | тип | опис |
|---|---|---|
| id | PK | |
| name | str | "90 Days" |
| duration_days | int | 35 / 90 / 400 |
| price_usd | int | 29 / 59 / 120 |
| is_active | bool | |
| description | str? | |

### subscriptions

| поле | тип | опис |
|---|---|---|
| id | PK | |
| user_id | FK users | |
| plan_id | FK plans | |
| started_at / expires_at | tz timestamp | `expires_at` індексований |
| status | enum(active, expired, cancelled) | |
| reminded_at | tz timestamp? | захист від дублювання нагадувань |

### payments

| поле | тип | опис |
|---|---|---|
| id | PK | |
| user_id / plan_id | FK | |
| method | enum(bitcoin, usdt, skrill, paypal, google_pay, neteller) | |
| amount_usd | numeric(10,2) | |
| status | enum(pending, paid, expired, failed) | |
| provider_ref | str? | адреса / checkout_id / мерчант-id |
| payload | jsonb? | доп. дані (private_key для USDT, meta) |
| paid_at | tz timestamp? | |

### payment_wallets (крипто)

| поле | тип | опис |
|---|---|---|
| id | PK | |
| payment_id | FK unique | |
| method | enum | |
| address | str | |
| network | str | btc-main / trc20 |
| used | bool | |

### invite_links

| поле | тип | опис |
|---|---|---|
| id | PK | |
| user_id | FK | |
| subscription_id | FK? | |
| url | str | |
| expires_at | tz timestamp? | |
| used | bool | |

### Зв'язки

```
user 1─N subscriptions N─1 plan
user 1─N payments
payment 1─0..1 payment_wallets
user 1─N invite_links
```

---

## 3. Шари (чиста архітектура)

```
src/
├── core/          # без залежностей: config, enums, exceptions, доменні правила (плани)
├── infra/
│   ├── db/        # моделі ORM + репозиторії (доступ до даних)
│   └── payments/  # інтерфейси провайдерів + реалізації (BTC, USDT, webhook, Stripe)
├── application/   # use-cases: PaymentService, SubscriptionService, Scheduler
└── presentation/  # aiogram: routers, keyboards, FSM, texts
```

Залежності: `presentation → application → infra`; `core` ні від чого не залежить.
`application` залежить від **інтерфейсів** (портів) з `infra/payments`, а не від конкретики.

---

## 4. Платіжні провайдери (абстракція)

```python
class PaymentProvider(Protocol):
    async def create(self, payment: Payment, plan: Plan) -> ProviderSession:
        """Створює платіж: повертає адресу / checkout-url / reference"""
    async def check(self, payment: Payment) -> bool:
        """Опитування: чи надійшли гроші (крипто)"""
    async def handle_webhook(self, payload: dict) -> str | None:
        """Повертає provider_ref, якщо платіж підтверджено"""
```

Реалізації:

| Провайдер | create | check | handle_webhook |
|---|---|---|---|
| **Bitcoin** (BlockCypher) | нова адреса | баланс ≥ суми | подія BlockCypher |
| **USDT** (TronGrid) | нова TRON-адреса (tronpy) | TRC20-трансфери | — |
| **Skrill/PayPal/Neteller** | reference для мерчанта | — | IPN/webhook провайдера |
| **Stripe** (Google Pay/картки) | checkout-session URL | — | `checkout.session.completed` + перевірка сигнатури |

Фабрика `provider_for(method)` повертає потрібну реалізацію. Увесь бізнес-флоу працює
через цей інтерфейс — додавати нові методи можна без змін ядра.

---

## 5. Ключові потоки

### Покупка

```
/plans → choose plan → choose method
  → PaymentService.create(user, plan, method)
      → provider.create() → Payment(status=pending, provider_ref)
      → повідомлення юзеру (адреса + QR або checkout-url)
```

### Підтвердження (єдина точка)

`PaymentService.confirm(payment)`:
1. idempotent — перевірка `status == pending`
2. mark paid + paid_at
3. `SubscriptionService.activate()` → продовжити/створити підписку + одноразовий
   invite-лінк (`member_limit=1`) + ревокат старих невикористаних лінків
4. повідомлення юзеру з лінком

Джерела підтвердження:
- **крипто (опитування):** scheduler → `provider.check()` → confirm
- **webhook:** `POST /webhook/{method}` → валідація секрету/сигнатури →
  `provider.handle_webhook()` → confirm

### Фонові задачі (scheduler)

| Задача | Період | Логіка |
|---|---|---|
| crypto_poll | `CRYPTO_POLL_INTERVAL` сек | `provider.check()` по pending крипто → confirm |
| renew_reminders | 1 год | підписки закінчуються за N днів і `reminded_at IS NULL` → нагадати |
| expire_subs | 10 хв | прострочені → `kick_member` з каналу + status=expired |
| stale_payments | 1 год | pending старші TTL → expired + повідомити юзера |

### Продовження підписки

Якщо є активна підписка — новий термін **додається до `expires_at`** (не починається
з сьогодні). Продовження не дублює запис.

---

## 6. План робіт по кроках

1. **core** — конфіг, enums, плани, виключення
2. **infra/db** — моделі + репозиторії + **Alembic** (не create_all)
3. **infra/payments** — порт + провайдери (BTC/USDT + webhook-заглушки)
4. **application** — PaymentService (create/confirm/webhook/poll),
   SubscriptionService (activate/expire/remind), Scheduler
5. **presentation** — бот-флоу, адмін-панель (stats/members/broadcast)
6. **вебхук-сервер** + entrypoint
7. **тести** — спочатку юніт на confirm/activate (idempotency, продовження),
   потім інтеграційні з тестовим Postgres
8. **Stripe** — окремим кроком, якщо потрібні Google Pay / картки

---

## 7. Зафіксовані рішення

- **Порти в ядрі:** ядро не знає про HTTP/Telegram — все через інтерфейси, легко
  тестити (mock провайдера).
- **Idempotent confirm:** платіж підтверджується один раз; подвійний webhook/poll
  не дублює підписку.
- **Продовження** додається до `expires_at` активної підписки.
- **Alembic** з першого дня.
- **Webhook-секрет обов'язковий у проді**; для Stripe — перевірка сигнатури.
- **USDT-ключі:** окрема задача — автопереказ на основний гаманець, або провайдер
  з hosted-wallet, якщо не хочеться керувати ключами.
- **Invite-link:** `member_limit=1`, завжди ревокат старого при новому; зберігати
  в БД для повторного надсилання (команда `/invite`).
- **Економія:** Bitcoin/USDT готові до запуску безкоштовно (без мерчант-акаунтів).
  PayPal/Skrill/Neteller — власні PSP з webhooks. Google Pay — лише через Stripe.
