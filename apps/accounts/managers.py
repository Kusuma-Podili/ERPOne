"""
Custom User and Account Managers.
Implements robust email normalization, verification checks, and administrative user creation.
"""
from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone
from enterpriseone.configuration.constants import AccountStatus


class UserManager(BaseUserManager):
    """
    Custom user manager using case-insensitive email as the unique identifier.
    """

    def create_user(self, email: str, password: str = None, **extra_fields):
        """
        Create and persist a standard enterprise user.
        """
        if not email:
            raise ValueError("The Email address must be provided.")

        email = self.normalize_email(email).lower().strip()
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("account_status", AccountStatus.ACTIVE)

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        """
        Create and persist an enterprise Super Administrator.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("account_status", AccountStatus.ACTIVE)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

    def active_users(self):
        """Filter users with active account status."""
        return self.filter(is_active=True, account_status=AccountStatus.ACTIVE)

    def locked_users(self):
        """Filter users currently experiencing account lockout."""
        return self.filter(locked_until__gt=timezone.now())

    def get_by_email(self, email: str):
        """Case-insensitive user lookup by email."""
        if not email:
            return None
        return self.filter(email__iexact=email.strip()).first()
