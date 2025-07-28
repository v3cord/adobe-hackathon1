# Specify the base image and platform architecture
FROM --platform=linux/amd64 python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the application folder into the container's working directory
COPY app/ .

# Install dependencies from the copied requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Define the command to run the script when the container starts
CMD ["python", "main.py"]