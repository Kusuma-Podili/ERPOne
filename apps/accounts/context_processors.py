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
        "is_user_admin": False,
        "is_user_employee": False,
        "is_user_customer": False,
        "user_role": "GUEST",
        "CURRENCY_SYMBOL": "₹",
        "CURRENCY_CODE": "INR",
    }

    if hasattr(request, "user") and request.user.is_authenticated:
        user = request.user
        context["user_display_role"] = user.display_role
        context["user_permissions"] = user.get_permissions_list()
        context["is_super_admin"] = user.is_superuser or user.has_role(SystemRole.SUPER_ADMIN)
        context["is_org_admin"] = user.has_role(SystemRole.ORG_ADMIN)
        context["is_manager"] = user.has_role(SystemRole.MANAGER)
        context["is_user_admin"] = getattr(user, "is_admin", False)
        context["is_user_employee"] = getattr(user, "is_employee", False)
        context["is_user_customer"] = getattr(user, "is_customer", False)
        context["user_role"] = getattr(user, "role", "EMPLOYEE")

        if hasattr(user, "profile"):
            context["user_theme"] = user.profile.theme

    return context
