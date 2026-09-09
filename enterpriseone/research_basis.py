"""Research references embedded in source for architectural traceability."""

RESEARCH_SOURCES = {
    "django_deployment": "https://docs.djangoproject.com/en/5.2/howto/deployment/",
    "owasp_asvs": "https://owasp.org/www-project-application-security-verification-standard/",
    "opentelemetry_python": "https://opentelemetry.io/docs/languages/python/",
    "celery_tasks": "https://docs.celeryq.dev/en/main/userguide/tasks.html",
    "twelve_factor_config": "https://www.12factor.net/config",
    "twelve_factor_logs": "https://12factor.net/logs",
    "twelve_factor_disposability": "https://12factor.net/disposability",
}

ARCHITECTURE_PRINCIPLES = (
    "separate configuration from code and keep credentials out of source",
    "use explicit security controls and verification tests",
    "use correlation-aware telemetry for traces and metrics",
    "design asynchronous work to be idempotent and retry-safe",
    "treat logs as event streams and preserve structured context",
    "prefer graceful startup and shutdown for operational processes",
)
