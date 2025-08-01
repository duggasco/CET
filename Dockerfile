FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY database.py .
COPY static ./static
COPY templates ./templates
COPY repositories ./repositories
COPY services ./services

# Create database on container start
RUN python database.py

# Expose port (default)
EXPOSE 9095

# Set environment variable for port
ENV FLASK_PORT=9095

# Run the application
CMD ["python", "app.py"]