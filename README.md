# Request Broker

An application that accepts requests with lists of ArchivesSpace URIs from users of our discovery system and for each item grabs data from ArchivesSpace. Formats that data for delivery to our item retrieval system (Aeon) for retrieval or digital duplication, or formats the data for email delivery or CSV download. Routes formatted data to retrieval management system or to an email for researcher use.

The request broker is part of [Project Electron](https://github.com/RockefellerArchiveCenter/project_electron), an initiative to build sustainable, open and user-centered infrastructure for the archival management of digital records at the [Rockefeller Archive Center](http://rockarch.org/).

## Setup

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

## Services

* Iterates over a list of request URIs and gets corresponding data from ArchivesSpace and parses over the data and marks it as submittable or unsubmittable.
* Converts AS data into strings and it to the message body of an email and then sends an email to an address or list of addresses.
* Creates retrieval and duplication transactions in Aeon by sending data to the Aeon API.

### Routes

| Method | URL | Parameters | Response  | Behavior  |
|--------|-----|---|---|---|
|POST|/api/deliver-request/email| |200|Delivers email messages containing data|
|POST|/api/process-request/parse| |200|Parses requests into a submittable and unsubmittable list|
|POST|/api/process-request/email| |200|Processes data in preparation for sending an email|
|POST|/api/download-csv/| |200|Downloads a CSV file of items|

## Requirements

Using this repo requires having [Docker](https://store.docker.com/search?type=edition&offering=community) installed.

## License

Code is released under an MIT License, as all your code should be. See [LICENSE](LICENSE) for details.
