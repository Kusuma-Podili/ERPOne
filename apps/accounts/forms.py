"""
Enterprise Accounts & Authentication Forms.
Provides forms for Login, Registration, Profile Updates, Password Changes, and Resets with validation.
"""
from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, UserProfile
from apps.accounts.validators import validate_work_email, validate_phone_number
from enterpriseone.configuration.constants import AccountStatus


class FormStylingMixin:
    """Applies modern enterprise styling classes to form widgets."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-check-input"})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-select enterprise-input"})
            else:
                field.widget.attrs.update({"class": "form-control enterprise-input"})


class EnterpriseLoginForm(FormStylingMixin, forms.Form):
    """
    Enterprise user login form with remember-me capability.
    """
    email = forms.EmailField(
        label=_("Email Address"),
        widget=forms.EmailInput(attrs={"placeholder": "you@enterprise.com", "autocomplete": "email"}),
        validators=[validate_work_email],
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Enter your password", "autocomplete": "current-password"}),
    )
    remember_me = forms.BooleanField(
        label=_("Remember this device for 14 days"),
        required=False,
        initial=False,
    )


class EnterpriseRegistrationForm(FormStylingMixin, forms.ModelForm):
    """
    Enterprise user self-registration form.
    """
    email = forms.EmailField(
        label=_("Work Email"),
        widget=forms.EmailInput(attrs={"placeholder": "name@company.com"}),
        validators=[validate_work_email],
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Create strong password"}),
    )
    password_confirm = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat password"}),
    )
    first_name = forms.CharField(
        label=_("First Name"),
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "John"}),
    )
    last_name = forms.CharField(
        label=_("Last Name"),
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Doe"}),
    )
    phone = forms.CharField(
        label=_("Phone Number"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "+1 (555) 000-0000"}),
        validators=[validate_phone_number],
    )
    job_title = forms.CharField(
        label=_("Job Title"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Operations Manager"}),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone", "job_title"]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account with this email address already exists."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm:
            if password != password_confirm:
                self.add_error("password_confirm", _("Passwords do not match."))
            else:
                user = User(email=cleaned_data.get("email", ""))
                password_validation.validate_password(password, user=user)

        return cleaned_data


class UserProfileForm(FormStylingMixin, forms.ModelForm):
    """
    User Preferences and Locale Profile Settings Form.
    """
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=30, required=False, validators=[validate_phone_number])
    job_title = forms.CharField(max_length=100, required=False)

    class Meta:
        model = UserProfile
        fields = [
            "department_name",
            "timezone",
            "language",
            "theme",
            "bio",
            "notification_email",
            "notification_inapp",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3, "placeholder": "Brief professional bio..."}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["phone"].initial = user.phone
            self.fields["job_title"].initial = user.job_title


class EnterprisePasswordChangeForm(FormStylingMixin, forms.Form):
    """
    User Password Change Form requiring verification of current password.
    """
    current_password = forms.CharField(
        label=_("Current Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Current password"}),
    )
    new_password = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "New secure password"}),
    )
    confirm_password = forms.CharField(
        label=_("Confirm New Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat new password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if not self.user.check_password(current_password):
            raise ValidationError(_("Your current password was entered incorrectly."))
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error("confirm_password", _("New passwords do not match."))
            else:
                password_validation.validate_password(new_password, user=self.user)

        return cleaned_data


class EnterprisePasswordResetForm(FormStylingMixin, forms.Form):
    """
    Password Reset request form looking up user by work email.
    """
    email = forms.EmailField(
        label=_("Registered Work Email"),
        widget=forms.EmailInput(attrs={"placeholder": "name@company.com"}),
        validators=[validate_work_email],
    )


class EnterpriseSetPasswordForm(FormStylingMixin, forms.Form):
    """
    Sets new password following token validation.
    """
    new_password = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Enter new password"}),
    )
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm new password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error("confirm_password", _("Passwords do not match."))
            else:
                password_validation.validate_password(new_password, user=self.user)

        return cleaned_data


class AdminUserCreateForm(FormStylingMixin, forms.ModelForm):
    """
    Administrative form to create users with role, organization, and status controls.
    """
    password = forms.CharField(
        label=_("Initial Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Temporary or initial password"}),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone", "job_title", "role", "account_status", "is_active", "is_verified"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "account_status" in self.fields:
            self.fields["account_status"].required = False
            self.fields["account_status"].initial = AccountStatus.ACTIVE

    def clean_account_status(self):
        status = self.cleaned_data.get("account_status")
        return status or AccountStatus.ACTIVE

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account with this email address already exists."))
        return email


class AdminUserEditForm(FormStylingMixin, forms.ModelForm):
    """
    Administrative form to update existing user role and status.
    """
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "job_title", "role", "account_status", "is_active", "is_verified"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "account_status" in self.fields:
            self.fields["account_status"].required = False

