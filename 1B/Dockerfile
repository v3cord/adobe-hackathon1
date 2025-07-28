# Use a slim Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /project

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all necessary project assets into the container
COPY src/ /project/src/
COPY models/ /project/models/
COPY app/input/ /project/app/input/

# Create the output directory so the script can write to it
RUN mkdir -p /project/app/output

# Define the entrypoint to run the main script
ENTRYPOINT ["python", "src/main.py"]