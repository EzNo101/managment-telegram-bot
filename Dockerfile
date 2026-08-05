FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Спершу залежності — для кешування шарів
COPY pyproject.toml uv.lock alembic.ini ./
COPY alembic ./alembic

RUN uv sync --no-dev --frozen --no-install-project

# Потім код
COPY src ./src
COPY main.py ./

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "main.py"]