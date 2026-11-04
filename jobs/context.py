import json
import os

from django.conf import settings


def request_context(request):
    """Resolve tenant and role from a bearer key, with headers for local demos only."""
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        try:
            keys = json.loads(os.getenv("PULSEOPS_API_KEYS", "{}"))
        except json.JSONDecodeError:
            keys = {}
        identity = keys.get(authorization.removeprefix("Bearer ").strip())
        if identity:
            return identity.get("tenant"), identity.get("role")
    if settings.DEBUG or settings.TESTING:
        return request.headers.get("X-Tenant-Id"), request.headers.get("X-User-Role")
    return None, None
