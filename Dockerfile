# Dockerfile for Ahmed Ragab's site — serves both the static site and the FastAPI backend.
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install backend dependencies first (better layer caching)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy everything (static site + backend)
COPY . /app

# Move the static site into a directory the backend will serve from
# (Static HTML/CSS/JS live at the repo root; backend is under /app/backend)
ENV STATIC_ROOT=/app

# Cloud Run injects PORT (default 8080). Uvicorn will bind to it.
EXPOSE 8080
ENV PORT=8080

WORKDIR /app/backend
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
