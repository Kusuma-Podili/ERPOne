"""
EnterpriseOne Master URL Configuration.
Routes requests across administrative, authentication, module, and API domains.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from django.shortcuts import redirect

def home_redirect(request):
    """Dynamic root landing page routing to role-specific dashboard."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if getattr(request.user, "is_admin", False):
        return redirect("accounts:dashboard")
    if getattr(request.user, "is_employee", False):
        return redirect("employee:dashboard")
    return redirect("customer:dashboard")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("employee/", include("apps.accounts.urls_employee", namespace="employee")),
    path("customer/", include("apps.accounts.urls_customer", namespace="customer")),
    path("organizations/", include("apps.organizations.urls", namespace="organizations")),
    path("crm/", include("apps.crm.urls", namespace="crm")),
    path("sales/", include("apps.sales.urls", namespace="sales")),
    path("inventory/", include("apps.inventory.urls", namespace="inventory")),
    path("procurement/", include("apps.procurement.urls", namespace="procurement")),
    path("finance/", include("apps.finance.urls", namespace="finance")),
    path("hr/", include("apps.hr.urls", namespace="hr")),
    path("payroll/", include("apps.payroll.urls", namespace="payroll")),
    path("projects/", include("apps.projects.urls", namespace="projects")),
    path("support/", include("apps.support.urls", namespace="support")),
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    path("ai/", include("apps.ai_engine.urls", namespace="ai_engine")),
    path("documents/", include("apps.documents.urls", namespace="documents")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("security/", include("apps.security.urls", namespace="security")),
    path("monitoring/", include("apps.monitoring.urls", namespace="monitoring")),
    path("integration/", include("apps.integration.urls", namespace="integration")),
    path("api/", include("enterpriseone.urls.api")),
    path("", home_redirect, name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
