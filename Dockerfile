# Use Python 3.11 as the base image
FROM python:3.11

# Set the working directory
WORKDIR /code

# Copy the requirements file and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application code
COPY ./app /code/app

# S# Command to run the FastAPI application
CMD ["fastapi", "run", "app/main.py", "--port", "80"]

