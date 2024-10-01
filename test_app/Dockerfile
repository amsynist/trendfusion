# Dockerfile
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the application code and requirements
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 80

# Command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]

