FROM python:3.10

ENV PYTHONUNBUFFERED 1
RUN apt-get update
RUN apt-get install --yes apache2 apache2-dev 
#RUN apt-get install --yes libapache2-mod-wsgi-py3
RUN apt-get install --yes postgresql
#RUN ln /usr/bin/python3 /usr/bin/python
RUN apt-get -y install python3-pip
RUN pip install --upgrade pip

RUN wget https://github.com/GrahamDumpleton/mod_wsgi/archive/refs/tags/4.9.0.tar.gz \
    && tar xvfz 4.9.0.tar.gz \
    && cd mod_wsgi-4.9.0 \
    && ./configure --with-apxs=/usr/bin/apxs --with-python=/usr/local/bin/python \
    && make \
    && make install \
    && make clean

ADD ./apache/000-request_broker.conf /etc/apache2/sites-available/000-request_broker.conf
RUN a2dissite 000-request_broker.conf
RUN a2ensite 000-request_broker.conf
RUN a2enmod headers
RUN a2enmod rewrite
RUN a2enmod wsgi

RUN mkdir -p /var/www/html/
COPY . /var/www/html/request-broker
WORKDIR /var/www/html/request-broker
RUN pip install -r requirements.txt
RUN ./manage.py collectstatic

RUN chmod 775 /var/www/html/request-broker
RUN chmod 775 /var/www/html/request-broker/static
RUN chown :www-data /var/www/html/request-broker
RUN chown :www-data /var/www/html/request-broker/static

EXPOSE 80 8001
CMD ["apache2ctl", "-D", "FOREGROUND"]
