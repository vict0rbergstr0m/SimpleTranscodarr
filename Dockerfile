# Use the official Python 3.10 image as the base
FROM python:3.10.12-slim

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update
RUN apt-get install -y ffmpeg
RUN apt-get install redis-server

# Copy the application code
COPY . .

# Expose the port
EXPOSE 8265

# Run the command to start the app #TODO: timeout should be 30 seconds when you fixed your multithreading shit
CMD ["gunicorn", "-w", "6", "-b", "0.0.0.0:8265", "--timeout", "300", "app:app"]