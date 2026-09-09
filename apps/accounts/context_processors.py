"""
Authentication and Role Template Context Processors.
Supplies global layout context: roles, permissions, theme preferences, and platform metadata.
"""
from enterpriseone.configuration.constants import PLATFORM_NAME, PLATFORM_VERSION, PLATFORM_TAGLINE
from enterpriseone.configuration.roles import SystemRole


def auth_context(request):
    """
    Injects contextual authentication, role, and platform data into all rendered templates.
    """
    context = {
        "PLATFORM_NAME": PLATFORM_NAME,
        "PLATFORM_VERSION": PLATFORM_VERSION,
        "PLATFORM_TAGLINE": PLATFORM_TAGLINE,
        "user_display_role": "Guest",
        "user_permissions": set(),
        "user_theme": "system",
        "is_super_admin": False,
        "is_org_admin": False,
        "is_manager": False,
    }

    if hasattr(request, "user") and request.user.is_authenticated:
        user = request.user
        context["user_display_role"] = user.display_role
        context["user_permissions"] = user.get_permissions_list()
        context["is_super_admin"] = user.is_superuser or user.has_role(SystemRole.SUPER_ADMIN)
        context["is_org_admin"] = user.has_role(SystemRole.ORG_ADMIN)
        context["is_manager"] = user.has_role(SystemRole.MANAGER)

        if hasattr(user, "profile"):
            context["user_theme"] = user.profile.theme

    return context
