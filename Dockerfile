# ================================================
# 🐳 Render Production Dockerfile for DrHealth
# ================================================

# Use lightweight Python base
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency list
COPY requirements.txt /tmp/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy entire project into the container
COPY . /app

# Set PYTHONPATH so "lib" and submodules are importable
ENV PYTHONPATH=/app

# Expose FastAPI port
EXPOSE 8000

# Run your FastAPI app
# (uses the app instance inside lib/ai_model/server_fastapi.py)
CMD ["uvicorn", "lib.ai_model.server_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
