"""
Testing settings for EnterpriseOne.
Optimized for high-speed in-memory testing and isolated test execution.
"""
from .base import *

DEBUG = False
TESTING = True

# Fast in-memory SQLite database for automated test suite
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast password hashing for testing speed
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable email delivery during testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Test security settings
AUTH_MAX_LOGIN_ATTEMPTS = 5
AUTH_LOCKOUT_DURATION_MINUTES = 15
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
