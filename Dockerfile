# Use a more recent, actively maintained Debian release as the base image.
# 'bullseye' is Debian 11, 'bookworm' is Debian 12.
# Using 'python:3.9-slim' without a specific Debian codename will usually
# point to the latest slim image for Python 3.9 on a supported Debian.
FROM python:3.9-slim # Changed from python:3.9-slim-buster

# Install PostgreSQL client libraries (libpq-dev) and build essentials
# These are required for psycopg2 to function correctly, even for -binary versions.
# --no-install-recommends helps keep the image size down.
# Ensure apt-get update succeeds with the new base image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port your Flask app listens on
EXPOSE 8080

# Command to run your Flask application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]