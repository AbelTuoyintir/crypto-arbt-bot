FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and config
COPY config/ config/
COPY src/ src/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 5000

CMD ["python", "src/dashboard/app.py"]
