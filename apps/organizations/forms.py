"""
Organizations Forms.
Forms for Organization, Branch, Location, Department, Team, Membership, and Invitations.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts.forms import FormStylingMixin
from apps.accounts.models import User, Role
from apps.organizations.models import (
    Organization,
    Location,
    Branch,
    Department,
    Team,
    OrganizationMember,
    OrganizationInvitation,
    OrganizationConfiguration,
)


class OrganizationForm(FormStylingMixin, forms.ModelForm):
    """Form to create or update an enterprise organization."""
    class Meta:
        model = Organization
        fields = [
            "name",
            "code",
            "slug",
            "registration_number",
            "tax_id",
            "currency",
            "fiscal_year_start_month",
            "website",
            "logo",
        ]


class LocationForm(FormStylingMixin, forms.ModelForm):
    """Form to add or edit an organizational physical facility."""
    class Meta:
        model = Location
        fields = [
            "name",
            "code",
            "address_line1",
            "address_line2",
            "city",
            "state_province",
            "postal_code",
            "country",
            "timezone",
            "phone",
            "email",
            "is_headquarters",
        ]


class BranchForm(FormStylingMixin, forms.ModelForm):
    """Form to add or edit an operational branch."""
    class Meta:
        model = Branch
        fields = ["name", "code", "location", "manager"]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["location"].queryset = Location.objects.filter(organization=organization, is_active=True)
            self.fields["manager"].queryset = User.objects.filter(
                organization_memberships__organization=organization, is_active=True
            )


class DepartmentForm(FormStylingMixin, forms.ModelForm):
    """Form to add or edit a department or cost center."""
    class Meta:
        model = Department
        fields = ["name", "code", "branch", "parent_department", "head_of_department", "budget_code", "description"]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["branch"].queryset = Branch.objects.filter(organization=organization, is_active=True)
            self.fields["parent_department"].queryset = Department.objects.filter(
                organization=organization, is_active=True
            )
            if self.instance and self.instance.pk:
                self.fields["parent_department"].queryset = self.fields["parent_department"].queryset.exclude(
                    pk=self.instance.pk
                )
            self.fields["head_of_department"].queryset = User.objects.filter(
                organization_memberships__organization=organization, is_active=True
            )


class TeamForm(FormStylingMixin, forms.ModelForm):
    """Form to add or edit an operational team."""
    class Meta:
        model = Team
        fields = ["name", "code", "department", "team_lead", "description"]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["department"].queryset = Department.objects.filter(organization=organization, is_active=True)
            self.fields["team_lead"].queryset = User.objects.filter(
                organization_memberships__organization=organization, is_active=True
            )


class OrganizationMemberForm(FormStylingMixin, forms.ModelForm):
    """Form to assign member details, reporting manager, and department."""
    class Meta:
        model = OrganizationMember
        fields = ["branch", "department", "reports_to", "job_title", "employee_id", "is_org_admin", "status"]

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["branch"].queryset = Branch.objects.filter(organization=organization, is_active=True)
            self.fields["department"].queryset = Department.objects.filter(organization=organization, is_active=True)
            self.fields["reports_to"].queryset = User.objects.filter(
                organization_memberships__organization=organization, is_active=True
            )
            if self.instance and self.instance.user_id:
                self.fields["reports_to"].queryset = self.fields["reports_to"].queryset.exclude(
                    id=self.instance.user_id
                )


class OrganizationInvitationForm(FormStylingMixin, forms.Form):
    """Form to issue email invitations to new enterprise staff."""
    email = forms.EmailField(
        label=_("Work Email Address"),
        widget=forms.EmailInput(attrs={"placeholder": "invitee@company.com"}),
    )
    job_title = forms.CharField(
        label=_("Job Title"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Senior Financial Analyst"}),
    )
    role = forms.ModelChoiceField(
        label=_("System Role"),
        queryset=Role.objects.all(),
        required=False,
    )
    branch = forms.ModelChoiceField(
        label=_("Assigned Branch"),
        queryset=Branch.objects.none(),
        required=False,
    )
    department = forms.ModelChoiceField(
        label=_("Assigned Department"),
        queryset=Department.objects.none(),
        required=False,
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["branch"].queryset = Branch.objects.filter(organization=organization, is_active=True)
            self.fields["department"].queryset = Department.objects.filter(organization=organization, is_active=True)


class OrganizationConfigurationForm(FormStylingMixin, forms.ModelForm):
    """Form to configure tenant policies and security rules."""
    class Meta:
        model = OrganizationConfiguration
        fields = [
            "allow_user_registration",
            "enforce_mfa",
            "session_timeout_minutes",
            "password_expiration_days",
        ]
