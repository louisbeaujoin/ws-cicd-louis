FROM python:3.12-slim

# Relie l'image (package ghcr.io) au dépôt GitHub
LABEL org.opencontainers.image.source="https://github.com/louisbeaujoin/ws-cicd-louis"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY static/ static/

# Version transmise au build, exposée à l'application
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# Utilisateur non-root
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
