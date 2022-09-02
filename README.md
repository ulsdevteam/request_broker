# Request Broker

An application that accepts requests with lists of ArchivesSpace URIs from users of our discovery system. For each item, the application fetches data from ArchivesSpace, formats that data for delivery to our retrieval management system (Aeon) to enable reading room or duplication requests, or formats the data for email delivery or CSV download. It routes formatted data to the retrieval system or to an email for researcher use. This is a passthrough service; users cannot create requests directly in the application.

The request broker is part of [Project Electron](https://github.com/RockefellerArchiveCenter/project_electron), an initiative to build sustainable, open and user-centered infrastructure for the archival management of digital records at the [Rockefeller Archive Center](http://rockarch.org/).

[![Build Status](https://travis-ci.com/RockefellerArchiveCenter/request_broker.svg?branch=base)](https://travis-ci.com/RockefellerArchiveCenter/request_broker)

## Getting Started

Install [git](https://git-scm.com/) and clone the repository

    $ git clone https://github.com/RockefellerArchiveCenter/request_broker.git

Install [Docker](https://store.docker.com/search?type=edition&offering=community) and run docker-compose from the root directory

    $ cd request_broker
    $ docker-compose build
    $ docker-compose up

Once the application starts successfully, you should be able to access the application in your browser at `http://localhost:8005`

When you're done, shut down docker-compose

    $ docker-compose down

Or, if you want to remove all data

    $ docker-compose down -v


## Configuration

The request broker manages configuration by setting environment variables. These variables can be seen in `docker-compose.yml`.

Deployment using the `Dockerfile.prod` file is intended to bring up a production image (based on Apache/WSGI) which is ready to be proxied publicly by an apache, nginx, traefik or similar frontend.  `Dockerfile.prod` expects two environment arguments to be available at build time: `REQUEST_BROKER_DNS` and `REQUEST_BROKER_PORT`.  Apache will Listen on `${REQUEST_BROKER_PORT}` with a ServerName of `${REQUEST_BROKER_DNS}`.

## Services

* Request Pre-Processing: Iterates over a list of request URIs, fetches corresponding data from ArchivesSpace, parses the data and marks it as submittable or unsubmittable.
* Mailer: correctly formats the body of an email message and sends an email to an address or list of addresses.
* Aeon Request Submission: creates retrieval and duplication transactions in Aeon by sending data to the Aeon API.
* CSV Download: formats parsed ArchivesSpace data into rows and columns for CSV download.

### Routes

| Method | URL | Parameters | Response  | Behavior  |
|--------|-----|---|---|---|
|POST|/api/deliver-request/email| |200|Delivers email messages containing data|
|POST|/api/process-request/parse| |200|Parses requests into a submittable and unsubmittable list|
|POST|/api/process-request/email| |200|Processes data in preparation for sending an email|
|POST|/api/download-csv/| |200|Downloads a CSV file of items|

## Development

This repository contains a configuration file for git [pre-commit](https://pre-commit.com/) hooks which help ensure that code is linted before it is checked into version control. It is strongly recommended that you install these hooks locally by installing pre-commit and running `pre-commit install`.

## License

Code is released under an MIT License, as all your code should be. See [LICENSE](LICENSE) for details.
