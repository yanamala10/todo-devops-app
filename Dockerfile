# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 for the Flask app
EXPOSE 5000

# Command to run the Flask app with Gunicorn
# 0.0.0.0 allows access from outside the container
# app:app refers to the 'app' variable in 'app.py'
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]