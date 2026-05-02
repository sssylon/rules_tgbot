# Builder stage: build wheels for all requirements
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential gcc libpq-dev libssl-dev pkg-config python3-dev \
  && pip install --upgrade pip setuptools wheel \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels
COPY requirements.txt pyproject.toml ./
RUN pip wheel --wheel-dir=/wheels -r requirements.txt

# Final stage: create minimal runtime image and install from built wheels
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# create non-root user for running the app
RUN addgroup --system bot && adduser --system --ingroup bot bot

WORKDIR /app

# Copy our pre-built wheels from builder
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
# Install from local wheels only
RUN pip install --no-index --find-links=/wheels -r requirements.txt

# Copy source
COPY . .
RUN chown -R bot:bot /app

# run as non-root user
USER bot

# minimal healthcheck script will be used by docker-compose
CMD ["python", "bot.py"]