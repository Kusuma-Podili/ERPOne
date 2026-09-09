"""
Accounts Application URL Routing.
"""
from django.urls import path
from apps.accounts.views import (
    EnterpriseLoginView,
    EnterpriseLogoutView,
    EnterpriseRegisterView,
    ActivateAccountView,
    EnterprisePasswordResetView,
    EnterprisePasswordResetConfirmView,
    DashboardView,
    UserProfileView,
    EnterprisePasswordChangeView,
    SecurityAuditView,
    UserListView,
    AdminUserCreateView,
    AdminUserEditView,
    AdminUserToggleStatusView,
    UnlockUserView,
)

app_name = "accounts"

urlpatterns = [
    # Authentication Lifecycle
    path("login/", EnterpriseLoginView.as_view(), name="login"),
    path("logout/", EnterpriseLogoutView.as_view(), name="logout"),
    path("register/", EnterpriseRegisterView.as_view(), name="register"),
    path("activate/<str:uidb64>/<str:token>/", ActivateAccountView.as_view(), name="activate"),
    path("password-reset/", EnterprisePasswordResetView.as_view(), name="password_reset"),
    path("password-reset-confirm/<str:uidb64>/<str:token>/", EnterprisePasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-change/", EnterprisePasswordChangeView.as_view(), name="password_change"),

    # Portal & Profile
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("security-audit/", SecurityAuditView.as_view(), name="security_audit"),

    # Administration
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/create/", AdminUserCreateView.as_view(), name="user_create"),
    path("users/<uuid:user_id>/edit/", AdminUserEditView.as_view(), name="user_edit"),
    path("users/<uuid:user_id>/toggle-status/", AdminUserToggleStatusView.as_view(), name="user_toggle_status"),
    path("users/<uuid:user_id>/unlock/", UnlockUserView.as_view(), name="unlock_user"),
]
