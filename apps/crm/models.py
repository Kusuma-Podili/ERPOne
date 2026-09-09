"""
Enterprise CRM Data Models.
Defines customer accounts, corporate relationships, and decision-maker contact directories.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import Organization


class AccountType(models.TextChoices):
    PROSPECT = "PROSPECT", _("Prospect")
    CUSTOMER = "CUSTOMER", _("Customer")
    PARTNER = "PARTNER", _("Strategic Partner")
    VENDOR = "VENDOR", _("Vendor / Supplier")
    RESELLER = "RESELLER", _("Value-Added Reseller")
    COMPETITOR = "COMPETITOR", _("Competitor")
    OTHER = "OTHER", _("Other")


class IndustryChoice(models.TextChoices):
    TECHNOLOGY = "TECHNOLOGY", _("Technology & Software")
    FINANCE = "FINANCE", _("Banking & Financial Services")
    HEALTHCARE = "HEALTHCARE", _("Healthcare & Pharmaceuticals")
    MANUFACTURING = "MANUFACTURING", _("Manufacturing & Industrial")
    RETAIL = "RETAIL", _("Retail & Consumer Goods")
    EDUCATION = "EDUCATION", _("Education & Academia")
    GOVERNMENT = "GOVERNMENT", _("Government & Public Sector")
    TELECOM = "TELECOM", _("Telecommunications")
    ENERGY = "ENERGY", _("Energy & Utilities")
    CONSULTING = "CONSULTING", _("Professional & Consulting Services")
    MEDIA = "MEDIA", _("Media & Entertainment")
    REAL_ESTATE = "REAL_ESTATE", _("Real Estate & Construction")
    OTHER = "OTHER", _("Other Industry")


class LifecycleStage(models.TextChoices):
    LEAD = "LEAD", _("Lead")
    MARKETING_QUALIFIED = "MQL", _("Marketing Qualified Lead (MQL)")
    SALES_QUALIFIED = "SQL", _("Sales Qualified Lead (SQL)")
    OPPORTUNITY = "OPPORTUNITY", _("Opportunity / In Pipeline")
    CUSTOMER = "CUSTOMER", _("Active Customer")
    EVANGELIST = "EVANGELIST", _("Evangelist / Advocate")
    CHURNED = "CHURNED", _("Churned Customer")


class AccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    INACTIVE = "INACTIVE", _("Inactive")
    ON_HOLD = "ON_HOLD", _("On Hold")
    ARCHIVED = "ARCHIVED", _("Archived")


class Account(models.Model):
    """
    Corporate or organizational client entity in the CRM subsystem.
    Scoped to an enterprise organization tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="crm_accounts",
        verbose_name=_("Organization"),
    )
    name = models.CharField(_("Account Name"), max_length=255, db_index=True)
    account_number = models.CharField(_("Account Number"), max_length=64, blank=True)
    account_type = models.CharField(
        _("Account Type"),
        max_length=32,
        choices=AccountType.choices,
        default=AccountType.PROSPECT,
        db_index=True,
    )
    industry = models.CharField(
        _("Industry"),
        max_length=32,
        choices=IndustryChoice.choices,
        default=IndustryChoice.TECHNOLOGY,
        db_index=True,
    )
    annual_revenue = models.DecimalField(
        _("Annual Revenue"),
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    employee_count = models.PositiveIntegerField(_("Employee Count"), null=True, blank=True)
    website = models.URLField(_("Corporate Website"), blank=True)
    phone = models.CharField(_("Primary Phone"), max_length=32, blank=True)
    email = models.EmailField(_("General Email"), blank=True)
    
    # Billing Address
    billing_address_line1 = models.CharField(_("Billing Address 1"), max_length=255, blank=True)
    billing_address_line2 = models.CharField(_("Billing Address 2"), max_length=255, blank=True)
    billing_city = models.CharField(_("Billing City"), max_length=100, blank=True)
    billing_state = models.CharField(_("Billing State / Province"), max_length=100, blank=True)
    billing_postal_code = models.CharField(_("Billing Postal Code"), max_length=32, blank=True)
    billing_country = models.CharField(_("Billing Country"), max_length=100, blank=True)

    # Shipping / Physical Address
    shipping_address_line1 = models.CharField(_("Shipping Address 1"), max_length=255, blank=True)
    shipping_address_line2 = models.CharField(_("Shipping Address 2"), max_length=255, blank=True)
    shipping_city = models.CharField(_("Shipping City"), max_length=100, blank=True)
    shipping_state = models.CharField(_("Shipping State / Province"), max_length=100, blank=True)
    shipping_postal_code = models.CharField(_("Shipping Postal Code"), max_length=32, blank=True)
    shipping_country = models.CharField(_("Shipping Country"), max_length=100, blank=True)

    # Lifecycle & Ownership
    lifecycle_stage = models.CharField(
        _("Lifecycle Stage"),
        max_length=32,
        choices=LifecycleStage.choices,
        default=LifecycleStage.LEAD,
        db_index=True,
    )
    status = models.CharField(
        _("Account Status"),
        max_length=32,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_accounts",
        verbose_name=_("Account Owner"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_accounts",
        verbose_name=_("Created By"),
    )
    description = models.TextField(_("Description / Background"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "name"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "lifecycle_stage"]),
            models.Index(fields=["organization", "account_type"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.account_number:
            # Auto-generate account number: ACC-YYYYMMDD-UUID[:6]
            import datetime
            date_prefix = datetime.date.today().strftime("%Y%m%d")
            self.account_number = f"ACC-{date_prefix}-{str(uuid.uuid4())[:6].upper()}"
        super().save(*args, **kwargs)

    @property
    def primary_contact(self):
        """Returns the primary contact associated with this account, if any."""
        return self.contacts.filter(is_primary_contact=True).first()

    @property
    def total_contacts_count(self) -> int:
        return self.contacts.count()

    @property
    def active_deals_count(self) -> int:
        if hasattr(self, "deals"):
            return self.deals.filter(is_closed=False).count()
        return 0

    @property
    def total_pipeline_value(self):
        if hasattr(self, "deals"):
            from django.db.models import Sum
            res = self.deals.filter(is_closed=False).aggregate(total=Sum("amount"))["total"]
            return res or 0
        return 0


class Contact(models.Model):
    """
    Individual contact or decision maker associated with a client account.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="crm_contacts",
        verbose_name=_("Organization"),
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name=_("Account / Company"),
    )
    first_name = models.CharField(_("First Name"), max_length=100)
    last_name = models.CharField(_("Last Name"), max_length=100)
    email = models.EmailField(_("Email Address"), db_index=True)
    phone = models.CharField(_("Direct Phone"), max_length=32, blank=True)
    mobile = models.CharField(_("Mobile Phone"), max_length=32, blank=True)
    job_title = models.CharField(_("Job Title"), max_length=128, blank=True)
    department = models.CharField(_("Department"), max_length=128, blank=True)
    is_primary_contact = models.BooleanField(_("Primary Contact Flag"), default=False)
    do_not_call = models.BooleanField(_("Do Not Call"), default=False)
    do_not_email = models.BooleanField(_("Do Not Email"), default=False)

    # Address
    address_line1 = models.CharField(_("Address Line 1"), max_length=255, blank=True)
    address_line2 = models.CharField(_("Address Line 2"), max_length=255, blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    state = models.CharField(_("State / Province"), max_length=100, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=32, blank=True)
    country = models.CharField(_("Country"), max_length=100, blank=True)

    lifecycle_stage = models.CharField(
        _("Lifecycle Stage"),
        max_length=32,
        choices=LifecycleStage.choices,
        default=LifecycleStage.LEAD,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_contacts",
        verbose_name=_("Contact Owner"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_contacts",
        verbose_name=_("Created By"),
    )
    notes = models.TextField(_("Internal Notes"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["organization", "last_name", "first_name"]),
            models.Index(fields=["account", "is_primary_contact"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        # If set to primary contact for an account, unset any existing primary contacts for that account
        if self.is_primary_contact and self.account_id:
            Contact.objects.filter(
                account_id=self.account_id,
                is_primary_contact=True
            ).exclude(pk=self.pk).update(is_primary_contact=False)
        super().save(*args, **kwargs)


class LeadSource(models.TextChoices):
    WEBSITE = "WEBSITE", _("Website Form / Inbound")
    REFERRAL = "REFERRAL", _("Client / Partner Referral")
    COLD_CALL = "COLD_CALL", _("Outbound Cold Call / Outreach")
    ADVERTISING = "ADVERTISING", _("Online Advertising / SEM")
    EVENT = "EVENT", _("Trade Show / Conference")
    PARTNER = "PARTNER", _("Channel Partner")
    SOCIAL_MEDIA = "SOCIAL_MEDIA", _("Social Media / LinkedIn")
    OTHER = "OTHER", _("Other Source")


class LeadStatus(models.TextChoices):
    NEW = "NEW", _("New / Uncontacted")
    CONTACTED = "CONTACTED", _("Contacted / In Discussion")
    QUALIFIED = "QUALIFIED", _("Sales Qualified")
    UNQUALIFIED = "UNQUALIFIED", _("Unqualified / Disqualified")
    CONVERTED = "CONVERTED", _("Converted to Customer")


class LeadPriority(models.TextChoices):
    LOW = "LOW", _("Low")
    MEDIUM = "MEDIUM", _("Medium")
    HIGH = "HIGH", _("High")
    URGENT = "URGENT", _("Urgent")


class Lead(models.Model):
    """
    Prospective customer or inbound business inquiry entity.
    Includes multi-factor algorithmic lead scoring and conversion tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="crm_leads",
        verbose_name=_("Organization"),
    )
    first_name = models.CharField(_("First Name"), max_length=100)
    last_name = models.CharField(_("Last Name"), max_length=100)
    company_name = models.CharField(_("Company Name"), max_length=255)
    job_title = models.CharField(_("Job Title"), max_length=128, blank=True)
    email = models.EmailField(_("Email Address"), db_index=True)
    phone = models.CharField(_("Phone"), max_length=32, blank=True)
    website = models.URLField(_("Company Website"), blank=True)
    lead_source = models.CharField(
        _("Lead Source"),
        max_length=32,
        choices=LeadSource.choices,
        default=LeadSource.WEBSITE,
        db_index=True,
    )
    status = models.CharField(
        _("Lead Status"),
        max_length=32,
        choices=LeadStatus.choices,
        default=LeadStatus.NEW,
        db_index=True,
    )
    priority = models.CharField(
        _("Priority"),
        max_length=16,
        choices=LeadPriority.choices,
        default=LeadPriority.MEDIUM,
        db_index=True,
    )
    estimated_value = models.DecimalField(
        _("Estimated Deal Value"),
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    lead_score = models.PositiveIntegerField(_("Algorithmic Lead Score (0-100)"), default=0, db_index=True)
    score_breakdown = models.JSONField(_("Score Calculation Breakdown"), default=dict, blank=True)
    industry = models.CharField(
        _("Industry"),
        max_length=32,
        choices=IndustryChoice.choices,
        default=IndustryChoice.TECHNOLOGY,
    )
    employee_count = models.PositiveIntegerField(_("Employee Count"), null=True, blank=True)
    annual_revenue = models.DecimalField(_("Annual Revenue"), max_digits=18, decimal_places=2, null=True, blank=True)

    # Address
    address_line1 = models.CharField(_("Address Line 1"), max_length=255, blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    state = models.CharField(_("State / Province"), max_length=100, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=32, blank=True)
    country = models.CharField(_("Country"), max_length=100, blank=True)

    # Ownership & Conversion
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_leads",
        verbose_name=_("Lead Owner"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_leads",
        verbose_name=_("Created By"),
    )
    is_converted = models.BooleanField(_("Converted Flag"), default=False, db_index=True)
    converted_at = models.DateTimeField(_("Conversion Timestamp"), null=True, blank=True)
    converted_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originating_leads",
        verbose_name=_("Converted Account"),
    )
    converted_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originating_leads",
        verbose_name=_("Converted Contact"),
    )
    notes = models.TextField(_("Internal Notes"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Lead")
        verbose_name_plural = _("Leads")
        ordering = ["-lead_score", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "lead_score"]),
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["organization", "is_converted"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.company_name})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class PipelineStage(models.Model):
    """
    Sales pipeline milestone stage for an organization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="crm_pipeline_stages",
        verbose_name=_("Organization"),
    )
    name = models.CharField(_("Stage Name"), max_length=100)
    code = models.CharField(_("Stage Code"), max_length=50)
    order = models.PositiveSmallIntegerField(_("Display Order"), default=1)
    default_probability = models.PositiveSmallIntegerField(
        _("Default Win Probability (%)"), default=10
    )
    is_won_stage = models.BooleanField(_("Closed Won Stage Flag"), default=False)
    is_lost_stage = models.BooleanField(_("Closed Lost Stage Flag"), default=False)
    is_active = models.BooleanField(_("Active Status"), default=True)
    color = models.CharField(_("Badge Color Hex"), max_length=20, default="#2563eb")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Pipeline Stage")
        verbose_name_plural = _("Pipeline Stages")
        ordering = ["order", "name"]
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(fields=["organization", "order"]),
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.default_probability}%)"


class Deal(models.Model):
    """
    Sales opportunity or deal tracking potential revenue through pipeline stages.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="crm_deals",
        verbose_name=_("Organization"),
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="deals",
        verbose_name=_("Corporate Account"),
    )
    primary_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
        verbose_name=_("Primary Contact"),
    )
    name = models.CharField(_("Deal Name"), max_length=255, db_index=True)
    deal_number = models.CharField(_("Deal Number"), max_length=64, blank=True)
    stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.PROTECT,
        related_name="deals",
        verbose_name=_("Current Pipeline Stage"),
    )
    amount = models.DecimalField(
        _("Total Contract Value ($)"),
        max_digits=18,
        decimal_places=2,
        default=0.00,
    )
    probability = models.PositiveSmallIntegerField(
        _("Win Probability (%)"), default=10
    )
    expected_close_date = models.DateField(_("Expected Close Date"), null=True, blank=True)
    actual_close_date = models.DateField(_("Actual Close Date"), null=True, blank=True)
    is_closed = models.BooleanField(_("Closed Flag"), default=False, db_index=True)
    is_won = models.BooleanField(_("Won Flag"), default=False, db_index=True)
    lost_reason = models.TextField(_("Reason for Loss"), blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_deals",
        verbose_name=_("Deal Owner"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_deals",
        verbose_name=_("Created By"),
    )
    description = models.TextField(_("Deal Overview / Scope"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Deal")
        verbose_name_plural = _("Deals")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "stage"]),
            models.Index(fields=["organization", "is_closed"]),
            models.Index(fields=["organization", "is_won"]),
            models.Index(fields=["account", "is_closed"]),
        ]

    def __str__(self):
        return f"{self.name} (${self.amount})"

    def save(self, *args, **kwargs):
        if not self.deal_number:
            import datetime
            date_prefix = datetime.date.today().strftime("%Y%m%d")
            self.deal_number = f"DEAL-{date_prefix}-{str(uuid.uuid4())[:6].upper()}"
        if not self.probability and self.stage_id:
            self.probability = self.stage.default_probability
        super().save(*args, **kwargs)

    @property
    def weighted_amount(self):
        from decimal import Decimal
        prob = Decimal(str(self.probability)) / Decimal("100")
        return self.amount * prob


class DealStageTransition(models.Model):
    """
    Immutable audit log entry recording each stage movement for a deal.
    Tracks velocity, timestamps, user responsible, and progression reasons.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="crm_deal_transitions",
        verbose_name=_("Organization"),
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="stage_transitions",
        verbose_name=_("Deal"),
    )
    from_stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Previous Stage"),
    )
    to_stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("Target Stage"),
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Changed By"),
    )
    transition_notes = models.TextField(_("Transition Notes"), blank=True)
    duration_in_previous_stage_seconds = models.PositiveIntegerField(
        _("Duration in Previous Stage (Seconds)"), null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Deal Stage Transition")
        verbose_name_plural = _("Deal Stage Transitions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["deal", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        from_name = self.from_stage.name if self.from_stage else "Creation"
        return f"{self.deal.name}: {from_name} -> {self.to_stage.name}"


class ActivityType(models.TextChoices):
    CALL = "CALL", _("Phone Call")
    MEETING = "MEETING", _("Meeting / Conference")
    TASK = "TASK", _("To-Do Task")
    EMAIL = "EMAIL", _("Email Correspondence")
    DEMO = "DEMO", _("Product Demonstration")
    NOTE = "NOTE", _("General Note")


class ActivityStatus(models.TextChoices):
    PLANNED = "PLANNED", _("Planned / Scheduled")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")


class ActivityPriority(models.TextChoices):
    LOW = "LOW", _("Low")
    NORMAL = "NORMAL", _("Normal")
    HIGH = "HIGH", _("High")
    URGENT = "URGENT", _("Urgent")


class Activity(models.Model):
    """
    Interaction, touchpoint, or scheduled task linked to accounts, contacts, leads, or deals.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="crm_activities",
        verbose_name=_("Organization"),
    )
    activity_type = models.CharField(
        _("Activity Type"),
        max_length=32,
        choices=ActivityType.choices,
        default=ActivityType.TASK,
        db_index=True,
    )
    subject = models.CharField(_("Subject / Title"), max_length=255)
    description = models.TextField(_("Description / Agenda / Notes"), blank=True)
    due_date = models.DateTimeField(_("Due Date / Scheduled Time"), null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(_("Completion Timestamp"), null=True, blank=True)
    status = models.CharField(
        _("Status"),
        max_length=32,
        choices=ActivityStatus.choices,
        default=ActivityStatus.PLANNED,
        db_index=True,
    )
    priority = models.CharField(
        _("Priority"),
        max_length=16,
        choices=ActivityPriority.choices,
        default=ActivityPriority.NORMAL,
    )
    # Linked entities
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("Account"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("Contact"),
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("Lead"),
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("Deal"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_crm_activities",
        verbose_name=_("Assigned Representative"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_activities",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")
        ordering = ["-due_date", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "due_date"]),
            models.Index(fields=["account", "status"]),
            models.Index(fields=["deal", "status"]),
        ]

    def __str__(self):
        return f"[{self.get_activity_type_display()}] {self.subject}"


class Note(models.Model):
    """
    Rich notes and documentation attached to CRM entities.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="crm_notes",
        verbose_name=_("Organization"),
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notes_list",
        verbose_name=_("Account"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notes_list",
        verbose_name=_("Contact"),
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notes_list",
        verbose_name=_("Deal"),
    )
    title = models.CharField(_("Note Title"), max_length=255)
    content = models.TextField(_("Content"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_notes",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Note")
        verbose_name_plural = _("Notes")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return self.title



