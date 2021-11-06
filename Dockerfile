FROM python:3.6-buster

ENV PYTHONUNBUFFERED 1
RUN apt-get update \
    && apt-get install -y \
      postgresql \
      netcat \
      apache2 \
      apache2-dev \
      libapache2-mod-wsgi-py3 \
    && rm -rf /var/lib/apt/lists/*

RUN a2dissite 000-default
COPY apache/django.dev.conf /etc/apache2/sites-available/request-broker.conf
RUN a2ensite request-broker.conf

WORKDIR /code
ADD requirements.txt /code/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ADD . /code/

ENTRYPOINT ["/code/entrypoint.sh"]
