from asnake.aspace import ASpace
from health_check.providers.health import ping
from request_broker import settings


def test_aspace():
    try:
        ASpace(baseurl=settings.ARCHIVESSPACE["baseurl"],
               username=settings.ARCHIVESSPACE["username"],
               password=settings.ARCHIVESSPACE["password"],
               repository=settings.ARCHIVESSPACE["repo_id"])
        return {"pong": True}
    except Exception as e:
        return {"error": str(e), "pong": False}


def ping_all():
    as_ping = test_aspace()
    system_ping = ping()
    return {"pong": all([m["pong"] for m in [system_ping, as_ping]])}
