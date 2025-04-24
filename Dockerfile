FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pydantic[email]

# Copy the rest of the application
COPY . .

# Set the entrypoint to run the server
ENTRYPOINT ["python", "main.py"]
