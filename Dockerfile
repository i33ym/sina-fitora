# Use Python 3.13 slim image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . /app/

# Create media directory
RUN mkdir -p /app/media

# Expose port
EXPOSE 8000

# Run migrations and start server with Daphne (for Django Channels)
CMD ["sh", "-c", "python manage.py migrate && daphne -b 0.0.0.0 -p 8000 fitora.asgi:application"]