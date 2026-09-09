FROM python:3.11-slim

WORKDIR /app

# Install git and system build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source code and workspace
COPY . /app

# Expose FastAPI default port
EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Start FastAPI server
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
