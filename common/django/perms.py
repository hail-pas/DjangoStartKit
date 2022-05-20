from django.contrib import auth
from django.core.exceptions import PermissionDenied


def _user_has_api_perm(user, method, uri):
    """check api based permission
    A backend can raise `PermissionDenied` to short-circuit permission checking.
    """
    for backend in auth.get_backends():
        if not hasattr(backend, "has_api_perm"):
            continue
        try:
            if backend.has_api_perm(user, method, uri):
                return True
        except PermissionDenied:
            return False
    return False
