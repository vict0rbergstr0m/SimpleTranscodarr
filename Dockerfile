# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install necessary packages
RUN apt-get update && apt-get install -y ffmpeg

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install flask

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV NAME TranscoderApp

# Run the application
CMD ["python", "app.py"]
