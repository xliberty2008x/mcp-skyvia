# Builder stage
FROM python:3.10-slim AS builder

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pydantic[email]

# Copy the rest of the application
COPY . .

# Final stage
FROM python:3.10-slim

WORKDIR /app

# Copy installed packages and application from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Properly formatted ENTRYPOINT
ENTRYPOINT ["python", "main.py"]
