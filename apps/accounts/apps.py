"""
Accounts Application Configuration.
"""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Enterprise Accounts & Authorization"

    def ready(self):
        # Register signals on startup
        import apps.accounts.signals  # noqa
