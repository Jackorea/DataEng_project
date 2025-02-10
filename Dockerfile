# Use an official Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy everything from the spiders directory
COPY movieScraper/movieScraper/spiders/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "script.py"]
