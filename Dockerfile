FROM python:3.10-buster

ENV PYTHONUNBUFFERED 1
RUN apt-get update \
    && apt-get install -y \
      postgresql \
      apache2 apache2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code
ADD requirements.txt /code/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ADD . /code/

ENTRYPOINT ["/code/entrypoint.sh"]
