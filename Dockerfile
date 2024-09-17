# Use Python 3.11 as the base image
FROM --platform=linux/amd64  python:3.11

# Set the working directory
WORKDIR /code

# Copy the requirements file and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application code
COPY ./app /code/app


# S# Command to run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0","--port","80"]
