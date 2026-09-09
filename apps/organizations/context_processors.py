"""
Organization Context Processors.
Provides active organization and user tenant memberships to templates.
"""
from apps.organizations.models import OrganizationMember


def organization_context(request):
    """
    Supplies active organization, member details, and tenant switch options to templates.
    """
    context = {
        "active_organization": getattr(request, "organization", None),
        "active_member": getattr(request, "organization_member", None),
        "user_organizations": [],
    }

    if hasattr(request, "user") and request.user.is_authenticated:
        memberships = OrganizationMember.objects.filter(
            user=request.user,
            status="ACTIVE",
            organization__is_active=True,
        ).select_related("organization")
        context["user_organizations"] = [m.organization for m in memberships]

    return context
