FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir build wheel

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home appuser

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY . .
RUN DJANGO_SECRET_KEY=build-only-secret-key \
    DJANGO_DEBUG=0 \
    DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "gunicorn edumanage.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 30"]
