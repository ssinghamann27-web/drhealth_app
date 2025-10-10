# ✅ Base image
FROM python:3.11-slim

# ✅ Working directory
WORKDIR /app

# ✅ Environment setup
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    PIP_NO_CACHE_DIR=1

# ✅ System dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    curl \
    libgl1 \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# ✅ Copy dependencies
COPY requirements.txt /tmp/requirements.txt

# ✅ Install all dependencies cleanly
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --force-reinstall psutil==5.9.8 && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ✅ Copy app files
COPY . /app

# ✅ Expose port
EXPOSE 8000

# ✅ Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

# ✅ Start FastAPI server
CMD ["uvicorn", "server_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
