from requests import Session

def http_meth_factory(meth):
    """Utility method for producing HTTP proxy methods.

    Urls are prefixed with the value of baseurl from the client's config.
    Arguments are passed unaltered to the matching requests.Session method."""

    def http_method(self, url, *args, **kwargs):
        full_url = "/".join([self.baseurl.rstrip("/"), url.lstrip("/")])
        return getattr(self.session, meth)(full_url, *args, **kwargs)
    return http_method


class ProxyMethods(type):
    """Metaclass to set up proxy methods for all requests-supported HTTP methods."""
    def __init__(cls, name, parents, dct):
        for meth in ("get", "post", "head", "put", "delete", "options",):
            fn = http_meth_factory(meth)
            fn.__name__ = meth
            fn.__doc__ = """Proxied :meth:`requests.Session.{}` method from :class:`requests.Session`""".format(meth)
            setattr(cls, meth, fn)


class AeonAPIClient(metaclass=ProxyMethods):

    def __init__(self, baseurl, apikey):
        self.baseurl = baseurl
        self.session = Session()
        self.session.headers.update(
            {"Accept": "application/json",
             "X-AEON-API-KEY": apikey})

    def get_reading_rooms(self):
        return self.get("ReadingRooms").json()

    def get_closures(self, reading_room_id):
        return self.get("/".join(["ReadingRooms", reading_room_id, "Closures"])).json()
