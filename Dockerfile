FROM python:3.11

WORKDIR /trendfusion

COPY ./requirements.txt /trendfusion/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /trendfusion/requirements.txt

COPY ./app /trendfusion/app

CMD ["fastapi", "run", "app/main.py", "--port", "80"]
