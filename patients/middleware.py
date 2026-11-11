import socket
from functools import lru_cache

from django.conf import settings
from django.http import HttpResponseRedirect

LOOPBACK_HOSTS = {"127.0.0.1", "localhost"}


@lru_cache(maxsize=1)
def _friendly_name_works() -> bool:
    """Only redirect when this PC's hosts file maps the name, otherwise the page would not load."""
    try:
        return socket.gethostbyname(settings.OPTILENS_HOSTNAME) == "127.0.0.1"
    except OSError:
        return False


class FriendlyHostRedirectMiddleware:
    """Show http://optilens:8002/ in the address bar instead of http://127.0.0.1:8002/."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host, _, port = request.get_host().partition(":")
        if host in LOOPBACK_HOSTS and _friendly_name_works():
            netloc = settings.OPTILENS_HOSTNAME + (f":{port}" if port else "")
            return HttpResponseRedirect(f"{request.scheme}://{netloc}{request.get_full_path()}")
        return self.get_response(request)
