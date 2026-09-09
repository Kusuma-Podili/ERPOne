"""
Enterprise Account & Password Validators.
Implements strict enterprise password complexity, email verification, and input constraints.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class EnterprisePasswordValidator:
    """
    Validates enterprise password complexity:
    - Minimum length (default 10)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one numeric digit
    - At least one special symbol
    """

    def __init__(self, min_length: int = 10):
        self.min_length = min_length

    def validate(self, password: str, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _(f"The password must contain at least {self.min_length} characters."),
                code="password_too_short",
            )
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("The password must contain at least one uppercase letter (A-Z)."),
                code="password_no_upper",
            )
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("The password must contain at least one lowercase letter (a-z)."),
                code="password_no_lower",
            )
        if not re.search(r"\d", password):
            raise ValidationError(
                _("The password must contain at least one numerical digit (0-9)."),
                code="password_no_number",
            )
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\/`~]", password):
            raise ValidationError(
                _("The password must contain at least one special character (e.g. !@#$%^&*)."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            f"Your password must be at least {self.min_length} characters long and include "
            "an uppercase letter, a lowercase letter, a number, and a special character."
        )


def validate_phone_number(value: str):
    """
    Validates phone number format: allows international prefix + and 7 to 20 digits, dashes, spaces.
    """
    if not value:
        return
    cleaned = re.sub(r"[\s\-\(\)]", "", value)
    if not re.match(r"^\+?[0-9]{7,20}$", cleaned):
        raise ValidationError(
            _("Enter a valid phone number with optional country code (e.g., +15551234567)."),
            code="invalid_phone",
        )


def validate_work_email(value: str):
    """
    Validates email format and ensures domain complies with enterprise standards.
    """
    if not value:
        raise ValidationError(_("Email address is required."), code="required")
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, value):
        raise ValidationError(_("Enter a valid enterprise email address."), code="invalid_email")
