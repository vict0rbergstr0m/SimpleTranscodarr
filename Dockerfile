# Use the official Python 3.10 image as the base
FROM python:3.10.12-slim

# Set environment variables to prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg and redis-server
RUN apt-get update && \
    apt-get install -y ffmpeg redis-server

# Copy the application code
COPY . .

# Expose the port for Flask app
EXPOSE 8265

# Expose the default Redis port
EXPOSE 6379

# Start Redis server in the background, then Gunicorn
CMD service redis-server start && \
    gunicorn -w 6 -b 0.0.0.0:8265 --timeout 30 app:app
