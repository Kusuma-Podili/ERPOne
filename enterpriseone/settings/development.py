"""
Development settings for EnterpriseOne.
Configures database engine with smart fallback and relaxed local development tools.
"""
import os
import socket
from .base import *

DEBUG = True

def _is_service_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """Helper to verify if a network service port is listening."""
    if not host or not port:
        return False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except Exception:
        return False

# Database Configuration with MySQL priority & frictionless SQLite fallback
db_engine = os.getenv("DATABASE_ENGINE", "sqlite3").lower()
db_host = os.getenv("DATABASE_HOST", "127.0.0.1")
db_port = int(os.getenv("DATABASE_PORT", "3306") or 3306)

if db_engine == "mysql" and _is_service_reachable(db_host, db_port):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DATABASE_NAME", "enterpriseone_db"),
            "USER": os.getenv("DATABASE_USER", "root"),
            "PASSWORD": os.getenv("DATABASE_PASSWORD", ""),
            "HOST": db_host,
            "PORT": str(db_port),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    # Use SQLite for local development and zero-configuration testing
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / os.getenv("SQLITE_DB_NAME", "db.sqlite3"),
        }
    }

# Disable HTTPS requirements for local development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Console email backend for local inspection
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
