"""
Enterprise Organization & Multi-Tenancy Models.
Defines Organization, Location, Branch, Department, Team, Member, TeamMembership, Invitation, and Configuration.
"""
import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User, Role


class Organization(models.Model):
    """
    Tenant Organization entity representing an enterprise or subsidiary.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Organization Name"), max_length=200)
    slug = models.SlugField(_("URL Identifier / Slug"), max_length=200, unique=True, db_index=True)
    code = models.CharField(_("Organization Code"), max_length=50, unique=True, db_index=True)
    registration_number = models.CharField(_("Business Registration Number"), max_length=100, blank=True)
    tax_id = models.CharField(_("Tax Identification Number"), max_length=100, blank=True)
    currency = models.CharField(_("Base Currency"), max_length=10, default="USD")
    fiscal_year_start_month = models.PositiveSmallIntegerField(_("Fiscal Year Start Month"), default=1)
    website = models.URLField(_("Corporate Website"), blank=True)
    logo = models.ImageField(_("Company Logo"), upload_to="org_logos/%Y/", blank=True, null=True)
    is_active = models.BooleanField(_("Active Status"), default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_members_count(self) -> int:
        return self.members.filter(status="ACTIVE").count()

    @property
    def total_branches_count(self) -> int:
        return self.branches.filter(is_active=True).count()

    @property
    def total_departments_count(self) -> int:
        return self.departments.filter(is_active=True).count()


class Location(models.Model):
    """
    Physical office, campus, or facility location for an organization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(_("Location Name"), max_length=150)
    code = models.CharField(_("Location Code"), max_length=50)
    address_line1 = models.CharField(_("Address Line 1"), max_length=255)
    address_line2 = models.CharField(_("Address Line 2"), max_length=255, blank=True)
    city = models.CharField(_("City"), max_length=100)
    state_province = models.CharField(_("State / Province"), max_length=100, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=30, blank=True)
    country = models.CharField(_("Country"), max_length=100, default="United States")
    timezone = models.CharField(_("Timezone"), max_length=50, default="UTC")
    phone = models.CharField(_("Phone Number"), max_length=30, blank=True)
    email = models.EmailField(_("Contact Email"), blank=True)
    is_headquarters = models.BooleanField(_("Headquarters Facility"), default=False)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")
        unique_together = ("organization", "code")
        ordering = ["-is_headquarters", "name"]

    def __str__(self):
        return f"{self.name} ({self.city}, {self.country})"


class Branch(models.Model):
    """
    Operational branch office operating within an organization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(_("Branch Name"), max_length=150)
    code = models.CharField(_("Branch Code"), max_length=50)
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="branches"
    )
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_branches"
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")
        unique_together = ("organization", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} [{self.code}]"


class Department(models.Model):
    """
    Functional department, division, or cost center. Supports recursive sub-departments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="departments")
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="departments"
    )
    parent_department = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="sub_departments"
    )
    name = models.CharField(_("Department Name"), max_length=150)
    code = models.CharField(_("Department Code"), max_length=50)
    head_of_department = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="headed_departments"
    )
    budget_code = models.CharField(_("Cost Center / Budget Code"), max_length=50, blank=True)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        unique_together = ("organization", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def full_department_path(self) -> str:
        """Returns breadcrumb-style hierarchical department name."""
        if self.parent_department:
            return f"{self.parent_department.full_department_path} > {self.name}"
        return self.name


class Team(models.Model):
    """
    Operational cross-functional team within a department.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(_("Team Name"), max_length=150)
    code = models.CharField(_("Team Code"), max_length=50)
    team_lead = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="led_teams"
    )
    description = models.TextField(_("Team Purpose & Charter"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Team")
        verbose_name_plural = _("Teams")
        unique_together = ("department", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class OrganizationMember(models.Model):
    """
    Organization employee / member relationship binding User to Organization, Branch, Department, and Manager.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organization_memberships")
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="members"
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="members"
    )
    reports_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="direct_subordinates"
    )
    employee_id = models.CharField(_("Employee ID"), max_length=50, blank=True)
    job_title = models.CharField(_("Corporate Job Title"), max_length=100, blank=True)
    is_org_admin = models.BooleanField(_("Organization Administrator"), default=False)
    status = models.CharField(_("Member Status"), max_length=30, default="ACTIVE", db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Organization Member")
        verbose_name_plural = _("Organization Members")
        unique_together = ("organization", "user")
        ordering = ["-is_org_admin", "user__last_name"]

    def __str__(self):
        return f"{self.user.get_full_name()} @ {self.organization.name}"


class TeamMembership(models.Model):
    """
    Junction linking an OrganizationMember to an operational Team.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    member = models.ForeignKey(OrganizationMember, on_delete=models.CASCADE, related_name="team_memberships")
    role_in_team = models.CharField(_("Role in Team"), max_length=50, default="MEMBER")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Team Membership")
        verbose_name_plural = _("Team Memberships")
        unique_together = ("team", "member")

    def __str__(self):
        return f"{self.member.user.get_full_name()} in {self.team.name} ({self.role_in_team})"


class OrganizationInvitation(models.Model):
    """
    Secure tokenized email invitation to join an organization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField(_("Invitee Email"), db_index=True)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_org_invitations"
    )
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    job_title = models.CharField(_("Assigned Job Title"), max_length=100, blank=True)
    token = models.CharField(_("Invitation Token"), max_length=128, unique=True, db_index=True)
    status = models.CharField(_("Invitation Status"), max_length=30, default="PENDING")
    expires_at = models.DateTimeField(_("Expires At"), db_index=True)
    accepted_at = models.DateTimeField(_("Accepted At"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Organization Invitation")
        verbose_name_plural = _("Organization Invitations")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation for {self.email} to {self.organization.name}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at < timezone.now()


class OrganizationConfiguration(models.Model):
    """
    Organization-level security policies, authentication restrictions, and tenant flags.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="configuration")
    allow_user_registration = models.BooleanField(_("Allow Self Registration"), default=True)
    enforce_mfa = models.BooleanField(_("Enforce Multi-Factor Authentication"), default=False)
    session_timeout_minutes = models.PositiveIntegerField(_("Session Timeout (Minutes)"), default=60)
    password_expiration_days = models.PositiveIntegerField(_("Password Rotation Days"), default=90)
    settings_json = models.JSONField(_("Custom Tenant Preferences"), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Organization Configuration")
        verbose_name_plural = _("Organization Configurations")

    def __str__(self):
        return f"Config: {self.organization.name}"
