import json
import random
import string
from os.path import join

from request_broker import settings

FIXTURES_DIR = join(settings.BASE_DIR, "fixtures")


def random_string(length=20):
    """Returns a random string of specified length."""
    return "".join(random.choice(string.ascii_letters) for m in range(length))


def random_list():
    """Returns a random list."""
    return random.sample(string.ascii_lowercase, random.randint(2, 10))


def json_from_fixture(filename):
    """Gets json information from a file.

    Args:
        filename (string): a file to read.

    Returns:
        dict: json data from the file.
    """
    with open(join(FIXTURES_DIR, filename), "r") as df:
        return json.load(df)
