"""
Enterprise Security Middleware.
Hardens HTTP response headers and provides client IP and device contextual resolution.
"""
from typing import Callable
from django.http import HttpRequest, HttpResponse


def get_client_ip(request: HttpRequest) -> str:
    """
    Extract reliable client IP address handling forward proxies and load balancers.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
    return ip


def get_client_user_agent(request: HttpRequest) -> str:
    """
    Extract truncated client user agent string for security audit logs.
    """
    ua = request.META.get("HTTP_USER_AGENT", "Unknown")
    return ua[:500] if ua else "Unknown"


class EnterpriseSecurityMiddleware:
    """
    Middleware applying strict enterprise HTTP headers and attaching client context.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Attach client IP and User Agent to request for easy access in views and services
        request.client_ip = get_client_ip(request)
        request.client_user_agent = get_client_user_agent(request)

        response = self.get_response(request)

        # Enterprise Security Headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
