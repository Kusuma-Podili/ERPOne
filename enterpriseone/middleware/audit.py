"""
Audit Context Middleware.
Maintains thread-local context for the active request to support automated auditing throughout domain services.
"""
import threading
from typing import Callable, Optional
from django.http import HttpRequest, HttpResponse

_thread_locals = threading.local()


def get_current_request() -> Optional[HttpRequest]:
    """Retrieve current thread-local HTTP request."""
    return getattr(_thread_locals, "request", None)


def get_current_user():
    """Retrieve current user from active request thread context."""
    request = get_current_request()
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user
    return None


class AuditContextMiddleware:
    """
    Sets thread-local references for the current HTTP request during request handling
    and cleans them up on response to prevent memory leaks across worker threads.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        _thread_locals.request = request
        try:
            response = self.get_response(request)
        finally:
            _thread_locals.request = None
        return response
