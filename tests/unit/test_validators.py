"""
Unit Tests for Enterprise Validators.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.validators import (
    EnterprisePasswordValidator,
    validate_phone_number,
    validate_work_email,
)


class ValidatorsTestCase(TestCase):
    """
    Validates password complexity rules, phone formatting, and work email validation.
    """

    def setUp(self):
        self.validator = EnterprisePasswordValidator(min_length=10)

    def test_compliant_password_passes(self):
        try:
            self.validator.validate("EnterpriseSecure#2026")
        except ValidationError:
            self.fail("Compliant password should not raise ValidationError.")

    def test_password_too_short_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("Pass1#")
        self.assertEqual(ctx.exception.code, "password_too_short")

    def test_password_missing_uppercase_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("enterprise_pass1#")
        self.assertEqual(ctx.exception.code, "password_no_upper")

    def test_password_missing_lowercase_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("ENTERPRISE_PASS1#")
        self.assertEqual(ctx.exception.code, "password_no_lower")

    def test_password_missing_number_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("EnterprisePass#")
        self.assertEqual(ctx.exception.code, "password_no_number")

    def test_password_missing_special_char_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("EnterprisePass2026")
        self.assertEqual(ctx.exception.code, "password_no_special")

    def test_valid_phone_numbers(self):
        valid_phones = ["+15551234567", "+442071838750", "555-123-4567", "(555) 123-4567"]
        for phone in valid_phones:
            try:
                validate_phone_number(phone)
            except ValidationError:
                self.fail(f"Valid phone {phone} raised ValidationError.")

    def test_invalid_phone_numbers(self):
        invalid_phones = ["123", "abc123456", "+++", "!@#$%"]
        for phone in invalid_phones:
            with self.assertRaises(ValidationError):
                validate_phone_number(phone)

    def test_valid_work_email(self):
        try:
            validate_work_email("executive@enterpriseone.com")
        except ValidationError:
            self.fail("Valid enterprise email raised ValidationError.")

    def test_invalid_work_email(self):
        invalid_emails = ["not-an-email", "@nodomain.com", "missing_at.com", ""]
        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                validate_work_email(email)
