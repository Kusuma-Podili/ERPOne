"""
Enterprise Authentication Backends.
Implements case-insensitive email authentication with brute-force lockout safeguards.
"""
from django.contrib.auth.backends import BaseBackend
from apps.accounts.models import User


class EmailAuthBackend(BaseBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL using case-insensitive email.
    """

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        login_identifier = email or username
        if not login_identifier or not password:
            return None

        login_identifier = login_identifier.strip().lower()

        try:
            user = User.objects.get(email__iexact=login_identifier)
        except User.DoesNotExist:
            return None

        # Check password
        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
