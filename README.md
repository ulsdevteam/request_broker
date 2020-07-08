# Request Broker

An application to process retrieval and duplication requests from our discovery system, and route relevant item data to our retrieval management system and back to researchers.

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

### Routes

## Requirements

Using this repo requires having [Docker](https://store.docker.com/search?type=edition&offering=community) installed.


## License

Code is released under an MIT License, as all your code should be. See [LICENSE](LICENSE) for details.
