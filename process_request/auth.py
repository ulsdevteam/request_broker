from request_broker import settings
from rest_framework.permissions import BasePermission


class AllowedListPermission(BasePermission):
    """Ensure the request's IP address is on the safe list configured in Django settings."""

    def has_permission(self, request, view):

        remote_addr = request.META['REMOTE_ADDR']

        for valid_ip in settings.ALLOWED_IPS:
            if remote_addr == valid_ip or remote_addr.startswith(valid_ip):
                return True

        return False
