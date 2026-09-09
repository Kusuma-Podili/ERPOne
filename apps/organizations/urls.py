"""
Organizations URL Patterns.
"""
from django.urls import path
from apps.organizations.views import (
    OrganizationDashboardView,
    OrganizationCreateView,
    TenantSwitchView,
    BranchListView,
    BranchCreateView,
    DepartmentListView,
    DepartmentCreateView,
    TeamListView,
    TeamCreateView,
    OrganizationMemberListView,
    MemberEditView,
    HierarchyTreeView,
    InvitationListView,
    InvitationCreateView,
    AcceptInvitationView,
    OrganizationSettingsView,
)

app_name = "organizations"

urlpatterns = [
    path("", OrganizationDashboardView.as_view(), name="dashboard"),
    path("create/", OrganizationCreateView.as_view(), name="create"),
    path("switch/<uuid:org_id>/", TenantSwitchView.as_view(), name="switch"),
    
    # Branches & Locations
    path("branches/", BranchListView.as_view(), name="branches"),
    path("branches/add/", BranchCreateView.as_view(), name="branch_create"),
    
    # Departments
    path("departments/", DepartmentListView.as_view(), name="departments"),
    path("departments/add/", DepartmentCreateView.as_view(), name="department_create"),
    
    # Teams
    path("teams/", TeamListView.as_view(), name="teams"),
    path("teams/add/", TeamCreateView.as_view(), name="team_create"),
    
    # Members & Reporting Tree
    path("members/", OrganizationMemberListView.as_view(), name="members"),
    path("members/<uuid:member_id>/edit/", MemberEditView.as_view(), name="member_edit"),
    path("hierarchy/", HierarchyTreeView.as_view(), name="hierarchy"),
    
    # Invitations
    path("invitations/", InvitationListView.as_view(), name="invitations"),
    path("invitations/create/", InvitationCreateView.as_view(), name="invitation_create"),
    path("invitations/<str:token>/accept/", AcceptInvitationView.as_view(), name="invitation_accept"),
    
    # Settings
    path("settings/", OrganizationSettingsView.as_view(), name="settings"),
]
