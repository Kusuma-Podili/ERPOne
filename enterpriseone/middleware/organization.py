"""
Organization Multi-Tenancy Middleware.
Resolves active tenant organization from session or user membership and attaches to request context.
"""
from typing import Callable, Optional
from django.http import HttpRequest, HttpResponse
from apps.organizations.models import Organization, OrganizationMember


class OrganizationContextMiddleware:
    """
    Identifies the active organization for an authenticated user and attaches
    `request.organization` and `request.organization_member` to the request pipeline.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.organization = None
        request.organization_member = None

        if hasattr(request, "user") and request.user.is_authenticated:
            # 1. Check session for explicitly selected active organization
            active_org_id = request.session.get("active_organization_id")
            if active_org_id:
                member = OrganizationMember.objects.filter(
                    organization_id=active_org_id,
                    user=request.user,
                    status__iexact="ACTIVE",
                ).select_related("organization", "branch", "department").first()

                if member and member.organization.is_active:
                    request.organization = member.organization
                    request.organization_member = member

            # 2. Fallback to user's primary active membership
            if not request.organization:
                member = OrganizationMember.objects.filter(
                    user=request.user,
                    status__iexact="ACTIVE",
                    organization__is_active=True,
                ).select_related("organization", "branch", "department").first()

                if member:
                    request.organization = member.organization
                    request.organization_member = member
                    request.session["active_organization_id"] = str(member.organization.id)

            # 3. Fallback for Customers via linked CRM Contact / Account
            if not request.organization and getattr(request.user, "is_customer", False):
                try:
                    from apps.crm.models import Contact
                    contact = getattr(request.user, "crm_contact", None) or Contact.objects.filter(email__iexact=request.user.email).first()
                    if contact and contact.organization:
                        request.organization = contact.organization
                        request.session["active_organization_id"] = str(contact.organization.id)
                except Exception:
                    pass

            # 4. Fail-safe fallback to default active organization for admins and staff
            if not request.organization:
                default_org = Organization.objects.filter(is_active=True).first()
                if default_org:
                    request.organization = default_org
                    request.session["active_organization_id"] = str(default_org.id)
                    member = OrganizationMember.objects.filter(
                        organization=default_org,
                        user=request.user,
                    ).first()
                    if not member and (request.user.is_superuser or getattr(request.user, "is_admin", False) or getattr(request.user, "is_employee", False)):
                        member, _ = OrganizationMember.objects.get_or_create(
                            organization=default_org,
                            user=request.user,
                            defaults={"status": "ACTIVE", "is_org_admin": getattr(request.user, "is_admin", False)}
                        )
                    request.organization_member = member

        response = self.get_response(request)
        return response
