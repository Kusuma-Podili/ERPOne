"""
Enterprise CRM Domain Services.
Provides algorithmic lead scoring and atomic lead-to-customer conversion workflows.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.crm.models import (
    Lead,
    LeadSource,
    LeadStatus,
    LeadPriority,
    Account,
    Contact,
    AccountType,
    LifecycleStage,
)


class LeadScoringService:
    """
    Algorithmic Lead Scoring Engine.
    Computes a weighted composite score (0 to 100) factoring demographic scale,
    data completeness, acquisition channel, organizational reputation, and velocity.
    """
    PUBLIC_EMAIL_DOMAINS = {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
        "mail.com",
        "proton.me",
        "zoho.com",
    }

    C_LEVEL_TITLES = {
        "ceo", "cto", "cfo", "coo", "cio", "cmo", "ciso", "cro",
        "chief", "president", "vice president", "vp", "director",
        "founder", "co-founder", "head", "managing director", "partner",
    }

    @classmethod
    def calculate_score(cls, lead: Lead) -> tuple[int, dict]:
        """
        Calculates the lead score and breakdown factors.
        Returns (total_score, breakdown_dict).
        """
        # 1. Demographic & Company Scale (Max 20 pts)
        demo_pts = 0
        if lead.employee_count:
            if lead.employee_count >= 500:
                demo_pts += 15
            elif lead.employee_count >= 100:
                demo_pts += 10
            elif lead.employee_count >= 20:
                demo_pts += 6
            else:
                demo_pts += 3

        if lead.annual_revenue:
            if lead.annual_revenue >= Decimal("10000000"):
                demo_pts += 5
            elif lead.annual_revenue >= Decimal("1000000"):
                demo_pts += 3
            elif lead.annual_revenue > 0:
                demo_pts += 1
        demo_pts = min(demo_pts, 20)

        # 2. Data Completeness (Max 25 pts)
        comp_pts = 0
        if lead.email and "@" in lead.email:
            comp_pts += 7
        if lead.phone:
            comp_pts += 5
        if lead.job_title:
            comp_pts += 5
            title_lower = lead.job_title.lower()
            if any(t in title_lower for t in cls.C_LEVEL_TITLES):
                comp_pts += 3  # Senior decision maker bonus
        if lead.company_name:
            comp_pts += 3
        if lead.city or lead.country or lead.address_line1:
            comp_pts += 2
        comp_pts = min(comp_pts, 25)

        # 3. Source Quality & Acquisition Channel (Max 20 pts)
        source_mapping = {
            LeadSource.REFERRAL: 20,
            LeadSource.PARTNER: 18,
            LeadSource.WEBSITE: 15,
            LeadSource.EVENT: 12,
            LeadSource.SOCIAL_MEDIA: 10,
            LeadSource.ADVERTISING: 8,
            LeadSource.COLD_CALL: 6,
            LeadSource.OTHER: 5,
        }
        source_pts = source_mapping.get(lead.lead_source, 5)

        # 4. Priority & Velocity Status (Max 15 pts)
        prio_pts = 0
        priority_mapping = {
            LeadPriority.URGENT: 10,
            LeadPriority.HIGH: 7,
            LeadPriority.MEDIUM: 4,
            LeadPriority.LOW: 1,
        }
        prio_pts += priority_mapping.get(lead.priority, 4)

        status_mapping = {
            LeadStatus.QUALIFIED: 5,
            LeadStatus.CONTACTED: 3,
            LeadStatus.NEW: 2,
            LeadStatus.UNQUALIFIED: 0,
            LeadStatus.CONVERTED: 5,
        }
        prio_pts += status_mapping.get(lead.status, 2)
        prio_pts = min(prio_pts, 15)

        # 5. Corporate Domain & Web Reputation (Max 20 pts)
        domain_pts = 0
        if lead.email and "@" in lead.email:
            domain = lead.email.split("@")[-1].strip().lower()
            if domain not in cls.PUBLIC_EMAIL_DOMAINS:
                domain_pts += 12  # Corporate proprietary domain
            else:
                domain_pts += 3
        if lead.website and len(lead.website.strip()) > 5:
            domain_pts += 8
        domain_pts = min(domain_pts, 20)

        # Total Aggregation
        total = demo_pts + comp_pts + source_pts + prio_pts + domain_pts
        total = max(0, min(100, total))

        breakdown = {
            "demographic": {"points": demo_pts, "max": 20},
            "completeness": {"points": comp_pts, "max": 25},
            "source": {"points": source_pts, "max": 20},
            "priority_status": {"points": prio_pts, "max": 15},
            "domain_reputation": {"points": domain_pts, "max": 20},
            "total": total,
        }
        return total, breakdown

    @classmethod
    def score_and_save(cls, lead: Lead) -> Lead:
        """
        Computes lead score and updates the model in-place.
        """
        score, breakdown = cls.calculate_score(lead)
        lead.lead_score = score
        lead.score_breakdown = breakdown
        lead.save(update_fields=["lead_score", "score_breakdown", "updated_at"])
        return lead


class LeadConversionService:
    """
    Executes atomic conversion of a sales-qualified Lead into
    a corporate Account, decision-maker Contact, and optional Deal.
    """
    @classmethod
    def convert_lead(
        cls,
        lead: Lead,
        create_account: bool = True,
        create_contact: bool = True,
        account_id: str = None,
        account_name: str = None,
        deal_name: str = None,
        deal_amount: Decimal = None,
        deal_stage_id: str = None,
        user = None,
    ) -> dict:
        """
        Executes atomic conversion with database transaction guarantees.
        """
        if lead.is_converted:
            raise ValidationError("This lead has already been converted into a customer account.")

        with transaction.atomic():
            account = None
            contact = None
            deal = None

            # 1. Resolve or Create Account
            if account_id:
                account = Account.objects.get(id=account_id, organization=lead.organization)
            elif create_account:
                final_account_name = (account_name or lead.company_name).strip()
                # Check for existing account with same name in org, else create
                account = Account.objects.filter(
                    organization=lead.organization,
                    name__iexact=final_account_name,
                ).first()
                if not account:
                    account = Account.objects.create(
                        organization=lead.organization,
                        name=final_account_name,
                        account_type=AccountType.CUSTOMER if lead.status == LeadStatus.QUALIFIED else AccountType.PROSPECT,
                        industry=lead.industry,
                        annual_revenue=lead.annual_revenue or lead.estimated_value,
                        employee_count=lead.employee_count,
                        website=lead.website,
                        phone=lead.phone,
                        email=lead.email,
                        billing_address_line1=lead.address_line1,
                        billing_city=lead.city,
                        billing_state=lead.state,
                        billing_postal_code=lead.postal_code,
                        billing_country=lead.country,
                        shipping_address_line1=lead.address_line1,
                        shipping_city=lead.city,
                        shipping_state=lead.state,
                        shipping_postal_code=lead.postal_code,
                        shipping_country=lead.country,
                        lifecycle_stage=LifecycleStage.OPPORTUNITY if deal_name else LifecycleStage.CUSTOMER,
                        owner=lead.owner or user,
                        created_by=user,
                        description=f"Converted from Lead: {lead.full_name} on {timezone.now().strftime('%Y-%m-%d')}\n\n{lead.notes}",
                    )

            # 2. Create Decision-Maker Contact
            if create_contact:
                contact = Contact.objects.create(
                    organization=lead.organization,
                    account=account,
                    first_name=lead.first_name,
                    last_name=lead.last_name,
                    email=lead.email,
                    phone=lead.phone,
                    job_title=lead.job_title,
                    is_primary_contact=True if account else False,
                    address_line1=lead.address_line1,
                    city=lead.city,
                    state=lead.state,
                    postal_code=lead.postal_code,
                    country=lead.country,
                    lifecycle_stage=LifecycleStage.CUSTOMER if lead.status == LeadStatus.QUALIFIED else LifecycleStage.SALES_QUALIFIED,
                    owner=lead.owner or user,
                    created_by=user,
                    notes=f"Converted from Lead dossier on {timezone.now().strftime('%Y-%m-%d')}.",
                )

            # 3. Create Deal if deal_name provided and Deal model exists
            if deal_name:
                try:
                    from apps.crm.models import Deal, PipelineStage
                    stage = None
                    if deal_stage_id:
                        stage = PipelineStage.objects.filter(id=deal_stage_id, organization=lead.organization).first()
                    if not stage:
                        stage = PipelineStage.objects.filter(organization=lead.organization).order_by("order").first()

                    deal = Deal.objects.create(
                        organization=lead.organization,
                        account=account,
                        primary_contact=contact,
                        name=deal_name.strip(),
                        stage=stage,
                        amount=deal_amount or lead.estimated_value or Decimal("0.00"),
                        owner=lead.owner or user,
                        created_by=user,
                        expected_close_date=timezone.now().date() + timezone.timedelta(days=30),
                    )
                except (ImportError, Exception):
                    deal = None

            # 4. Mark Lead as Converted
            lead.is_converted = True
            lead.status = LeadStatus.CONVERTED
            lead.converted_at = timezone.now()
            lead.converted_account = account
            lead.converted_contact = contact
            lead.save(update_fields=[
                "is_converted",
                "status",
                "converted_at",
                "converted_account",
                "converted_contact",
                "updated_at",
            ])

            return {
                "account": account,
                "contact": contact,
                "deal": deal,
            }


class PipelineService:
    """
    Sales Pipeline Management and Forecasting Engine.
    Handles stage lifecycle, default stage initialization, transitions, and revenue forecasting.
    """
    DEFAULT_STAGES = [
        {"name": "Prospecting", "code": "PROSPECTING", "order": 1, "default_probability": 10, "color": "#64748b", "is_won_stage": False, "is_lost_stage": False},
        {"name": "Discovery & Qualification", "code": "QUALIFICATION", "order": 2, "default_probability": 25, "color": "#0284c7", "is_won_stage": False, "is_lost_stage": False},
        {"name": "Proposal / Demonstration", "code": "PROPOSAL", "order": 3, "default_probability": 45, "color": "#2563eb", "is_won_stage": False, "is_lost_stage": False},
        {"name": "Negotiation & Review", "code": "NEGOTIATION", "order": 4, "default_probability": 70, "color": "#8b5cf6", "is_won_stage": False, "is_lost_stage": False},
        {"name": "Executive Commitment", "code": "COMMITMENT", "order": 5, "default_probability": 90, "color": "#f59e0b", "is_won_stage": False, "is_lost_stage": False},
        {"name": "Closed Won", "code": "CLOSED_WON", "order": 6, "default_probability": 100, "color": "#10b981", "is_won_stage": True, "is_lost_stage": False},
        {"name": "Closed Lost", "code": "CLOSED_LOST", "order": 7, "default_probability": 0, "color": "#ef4444", "is_won_stage": False, "is_lost_stage": True},
    ]

    @classmethod
    def initialize_default_stages(cls, organization) -> list:
        """
        Ensures the organization has the standard 7 pipeline stages configured.
        """
        from apps.crm.models import PipelineStage
        created_stages = []
        for stage_def in cls.DEFAULT_STAGES:
            stage, created = PipelineStage.objects.get_or_create(
                organization=organization,
                code=stage_def["code"],
                defaults={
                    "name": stage_def["name"],
                    "order": stage_def["order"],
                    "default_probability": stage_def["default_probability"],
                    "color": stage_def["color"],
                    "is_won_stage": stage_def["is_won_stage"],
                    "is_lost_stage": stage_def["is_lost_stage"],
                    "is_active": True,
                },
            )
            created_stages.append(stage)
        return created_stages

    @classmethod
    def transition_stage(
        cls,
        deal,
        to_stage,
        changed_by=None,
        transition_notes: str = "",
        lost_reason: str = "",
    ):
        """
        Advances or moves a deal to a new stage, calculates stage duration,
        and produces an immutable DealStageTransition audit log entry.
        """
        from apps.crm.models import DealStageTransition

        from_stage = deal.stage
        now = timezone.now()

        # Calculate duration in previous stage
        duration_seconds = None
        last_transition = deal.stage_transitions.first()
        if last_transition:
            duration_seconds = int((now - last_transition.created_at).total_seconds())
        elif deal.created_at:
            duration_seconds = int((now - deal.created_at).total_seconds())

        with transaction.atomic():
            # Update deal state
            deal.stage = to_stage
            deal.probability = to_stage.default_probability

            if to_stage.is_won_stage:
                deal.is_closed = True
                deal.is_won = True
                deal.actual_close_date = now.date()
                deal.lost_reason = ""
            elif to_stage.is_lost_stage:
                deal.is_closed = True
                deal.is_won = False
                deal.actual_close_date = now.date()
                if lost_reason:
                    deal.lost_reason = lost_reason
            else:
                deal.is_closed = False
                deal.is_won = False
                deal.actual_close_date = None

            deal.save(update_fields=[
                "stage", "probability", "is_closed", "is_won",
                "actual_close_date", "lost_reason", "updated_at",
            ])

            # Record transition log
            transition = DealStageTransition.objects.create(
                organization=deal.organization,
                deal=deal,
                from_stage=from_stage,
                to_stage=to_stage,
                changed_by=changed_by,
                transition_notes=transition_notes or (f"Lost Reason: {lost_reason}" if lost_reason else ""),
                duration_in_previous_stage_seconds=duration_seconds,
            )

        return transition

    @classmethod
    def calculate_pipeline_forecast(cls, organization) -> dict:
        """
        Computes pipeline metrics: Total Value, Weighted Forecast, Win Rate, and stage breakdown.
        """
        from apps.crm.models import Deal
        from django.db.models import Sum

        deals = Deal.objects.filter(organization=organization)
        open_deals = deals.filter(is_closed=False)
        won_deals = deals.filter(is_won=True)
        lost_deals = deals.filter(is_closed=True, is_won=False)

        total_pipeline = open_deals.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Weighted forecast: sum(amount * probability / 100)
        weighted_sum = Decimal("0.00")
        for d in open_deals:
            weighted_sum += d.weighted_amount

        won_revenue = won_deals.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        total_closed = won_deals.count() + lost_deals.count()
        win_rate = (won_deals.count() / total_closed * 100) if total_closed > 0 else 0.0

        return {
            "total_pipeline_value": total_pipeline,
            "weighted_forecast_value": weighted_sum,
            "won_revenue": won_revenue,
            "open_deals_count": open_deals.count(),
            "won_deals_count": won_deals.count(),
            "lost_deals_count": lost_deals.count(),
            "win_rate_percentage": round(win_rate, 1),
        }

