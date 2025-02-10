# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements first (to leverage Docker's caching mechanism)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Expose the port the app runs on (adjust if necessary)
EXPOSE 5000

# Define environment variables for MongoDB (adjust as needed)
ENV MONGO_URI=mongodb://mongodb:27017/

# Run the application
CMD ["python", "src/app.py"]
