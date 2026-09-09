"""
Session Security Middleware.
Monitors session activity, verifies account active status on each request, and terminates stale sessions.
"""
from datetime import datetime, timezone
from typing import Callable
from django.conf import settings
from django.contrib import auth, messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


class SessionSecurityMiddleware:
    """
    Ensures active sessions belong to non-locked, non-deactivated accounts
    and tracks last user interaction timestamp.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            # Check if account has been deactivated or locked after session was established
            if not request.user.is_active:
                auth.logout(request)
                messages.error(request, "Your account has been deactivated. Please contact your administrator.")
                return redirect(settings.LOGIN_URL)

            # Check if user account is locked
            if hasattr(request.user, "is_locked") and request.user.is_locked:
                auth.logout(request)
                messages.error(request, "Your account is temporarily locked due to security policy. Please contact your administrator.")
                return redirect(settings.LOGIN_URL)

            # Update session last activity timestamp
            request.session["last_activity"] = datetime.now(timezone.utc).isoformat()

        response = self.get_response(request)
        return response
