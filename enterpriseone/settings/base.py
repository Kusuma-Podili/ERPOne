"""
Base settings for EnterpriseOne.
Provides shared settings across development, testing, staging, and production environments.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file if it exists
load_dotenv(BASE_DIR / ".env")

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "enterpriseone-insecure-development-secret-key-fallback-999")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",") if h.strip()]

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
]

ENTERPRISE_APPS = [
    "apps.accounts.apps.AccountsConfig",
    "apps.organizations.apps.OrganizationsConfig",
    "apps.crm.apps.CrmConfig",
    "apps.sales.apps.SalesConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.procurement.apps.ProcurementConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + ENTERPRISE_APPS

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "enterpriseone.middleware.security.EnterpriseSecurityMiddleware",
    "enterpriseone.middleware.session.SessionSecurityMiddleware",
    "enterpriseone.middleware.organization.OrganizationContextMiddleware",
    "enterpriseone.middleware.audit.AuditContextMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "enterpriseone.urls.base"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.auth_context",
                "apps.organizations.context_processors.organization_context",
            ],
        },
    },
]

WSGI_APPLICATION = "enterpriseone.wsgi.application"
ASGI_APPLICATION = "enterpriseone.asgi.application"

# Custom User Model & Authentication Backends
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": int(os.getenv("AUTH_PASSWORD_MIN_LENGTH", "10"))},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "apps.accounts.validators.EnterprisePasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = os.getenv("STATIC_URL", "/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication & Security Policies
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:index"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_MAX_LOGIN_ATTEMPTS = int(os.getenv("AUTH_MAX_LOGIN_ATTEMPTS", "5"))
AUTH_LOCKOUT_DURATION_MINUTES = int(os.getenv("AUTH_LOCKOUT_DURATION_MINUTES", "15"))
SESSION_COOKIE_AGE = int(os.getenv("AUTH_SESSION_COOKIE_AGE_SECONDS", "86400"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv("AUTH_SESSION_EXPIRE_AT_BROWSER_CLOSE", "False").lower() in ("true", "1")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# Email backend configuration
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "EnterpriseOne <noreply@enterpriseone.internal>")
