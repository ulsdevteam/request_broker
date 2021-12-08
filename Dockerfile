FROM python:3.9

ENV PYTHONUNBUFFERED 1
RUN apt-get update
RUN apt-get install --yes apache2
RUN apt-get install --yes lib-apache2-mod-wsgi-py3
RUN apt-get install -- yes postgresql
RUN ln /usr/bin/python3 /usr/bin/python
RUN apt-get -y install python3-pip
RUN pip install --upgrade pip

ADD ./000-request-broker.conf /etc/apache2/sites-available/000-request-broker.conf
ADD ./requirements.txt /var/www/html/
RUN a2dissite 000-request-broker.conf
RUN a2ensite 000-request-broker.conf
RUN a2enmod headers
RUN a2enmod rewrite

RUN mkdir -p /var/www/html
COPY . /var/www/html/request-broker
WORKDIR /var/www/html/request-broker
RUN pip install -r requirements.txt
RUN ./manage.py collectstatic

RUN chmod 775 /var/www/html/request-broker
RUN chmod 775 /var/logs
RUN chmod 775 /var/www/html/request-broker/static
RUN chown :www-data /var/www/html/request-broker
RUN chown :www-data /var/logs
RUN chown :www-data /var/www/html/request-broker/static

EXPOSE 80 8001
CMD["apache2ctl", "-D", "FOREGROUND"]
