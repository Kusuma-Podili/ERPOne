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
                    status="ACTIVE",
                ).select_related("organization", "branch", "department").first()

                if member and member.organization.is_active:
                    request.organization = member.organization
                    request.organization_member = member

            # 2. Fallback to user's primary active membership
            if not request.organization:
                member = OrganizationMember.objects.filter(
                    user=request.user,
                    status="ACTIVE",
                    organization__is_active=True,
                ).select_related("organization", "branch", "department").first()

                if member:
                    request.organization = member.organization
                    request.organization_member = member
                    request.session["active_organization_id"] = str(member.organization.id)

        response = self.get_response(request)
        return response
