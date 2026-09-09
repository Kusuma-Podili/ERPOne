"""
Organizations Application Views.
Implements views for Organization Dashboard, Branches, Departments, Teams, Member Hierarchy, and Invitations.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView

from apps.accounts.permissions import RoleRequiredMixin
from apps.organizations.models import (
    Organization,
    Location,
    Branch,
    Department,
    Team,
    OrganizationMember,
    TeamMembership,
    OrganizationInvitation,
    OrganizationConfiguration,
)
from apps.organizations.forms import (
    OrganizationForm,
    LocationForm,
    BranchForm,
    DepartmentForm,
    TeamForm,
    OrganizationMemberForm,
    OrganizationInvitationForm,
    OrganizationConfigurationForm,
)
from apps.organizations.services import (
    OrganizationService,
    HierarchyService,
    InvitationService,
)
from enterpriseone.configuration.roles import SystemRole


class OrganizationAccessMixin(LoginRequiredMixin):
    """
    Ensures the user has an active organization resolved in the request pipeline.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not getattr(request, "organization", None):
            # If user has no active organization, redirect them to create or request one
            messages.info(request, "Please create or select an active organization to continue.")
            return redirect("organizations:create")

        return super().dispatch(request, *args, **kwargs)


class OrganizationDashboardView(OrganizationAccessMixin, TemplateView):
    """
    Executive dashboard for the active tenant organization.
    """
    template_name = "organizations/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["organization"] = org
        context["total_members"] = org.members.filter(status="ACTIVE").count()
        context["total_branches"] = org.branches.filter(is_active=True).count()
        context["total_departments"] = org.departments.filter(is_active=True).count()
        context["total_teams"] = Team.objects.filter(department__organization=org, is_active=True).count()
        context["recent_members"] = org.members.select_related("user", "department", "branch").order_by("-joined_at")[:5]
        context["pending_invitations_count"] = org.invitations.filter(status="PENDING").count()
        return context


class OrganizationCreateView(LoginRequiredMixin, View):
    """
    Allows a user or superuser to provision a new tenant organization.
    """
    template_name = "organizations/organization_form.html"

    def get(self, request):
        form = OrganizationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = OrganizationForm(request.POST, request.FILES)
        if form.is_valid():
            org = OrganizationService.create_organization(
                name=form.cleaned_data["name"],
                code=form.cleaned_data["code"],
                slug=form.cleaned_data.get("slug"),
                currency=form.cleaned_data.get("currency", "USD"),
                creator=request.user,
            )
            request.session["active_organization_id"] = str(org.id)
            messages.success(request, f"Organization '{org.name}' has been successfully provisioned!")
            return redirect("organizations:dashboard")
        return render(request, self.template_name, {"form": form})


class TenantSwitchView(LoginRequiredMixin, View):
    """
    Switches active organization context stored in the user's session.
    """
    def post(self, request, org_id):
        org = get_object_or_404(Organization, id=org_id, is_active=True)
        # Verify user is a member or superuser
        is_member = org.members.filter(user=request.user, status="ACTIVE").exists()
        if is_member or request.user.is_superuser:
            request.session["active_organization_id"] = str(org.id)
            messages.success(request, f"Switched to organization: {org.name}")
        else:
            messages.error(request, "You are not an active member of that organization.")
        return redirect("organizations:dashboard")


class BranchListView(OrganizationAccessMixin, ListView):
    """
    Lists branches and physical locations for the active organization.
    """
    template_name = "organizations/branch_list.html"
    context_object_name = "branches"

    def get_queryset(self):
        return Branch.objects.filter(organization=self.request.organization).select_related("location", "manager")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["locations"] = Location.objects.filter(organization=self.request.organization)
        return context


class BranchCreateView(OrganizationAccessMixin, RoleRequiredMixin, View):
    """
    Creates a new branch under the active organization.
    """
    template_name = "organizations/branch_form.html"
    required_roles = [SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN]

    def get(self, request):
        form = BranchForm(organization=request.organization)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = BranchForm(request.POST, organization=request.organization)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.organization = request.organization
            branch.save()
            messages.success(request, f"Branch '{branch.name}' created successfully.")
            return redirect("organizations:branches")
        return render(request, self.template_name, {"form": form})


class DepartmentListView(OrganizationAccessMixin, ListView):
    """
    Lists departments and cost centers for the active organization.
    """
    template_name = "organizations/department_list.html"
    context_object_name = "departments"

    def get_queryset(self):
        return Department.objects.filter(
            organization=self.request.organization
        ).select_related("head_of_department", "branch", "parent_department")


class DepartmentCreateView(OrganizationAccessMixin, RoleRequiredMixin, View):
    """
    Creates a new department within the active organization.
    """
    template_name = "organizations/department_form.html"
    required_roles = [SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN, SystemRole.MANAGER]

    def get(self, request):
        form = DepartmentForm(organization=request.organization)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = DepartmentForm(request.POST, organization=request.organization)
        if form.is_valid():
            dept = form.save(commit=False)
            dept.organization = request.organization
            dept.save()
            messages.success(request, f"Department '{dept.name}' created successfully.")
            return redirect("organizations:departments")
        return render(request, self.template_name, {"form": form})


class TeamListView(OrganizationAccessMixin, ListView):
    """
    Lists operational teams across departments.
    """
    template_name = "organizations/team_list.html"
    context_object_name = "teams"

    def get_queryset(self):
        return Team.objects.filter(
            department__organization=self.request.organization
        ).select_related("department", "team_lead")


class TeamCreateView(OrganizationAccessMixin, RoleRequiredMixin, View):
    """
    Creates an operational team within a department.
    """
    template_name = "organizations/team_form.html"
    required_roles = [SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN, SystemRole.MANAGER]

    def get(self, request):
        form = TeamForm(organization=request.organization)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = TeamForm(request.POST, organization=request.organization)
        if form.is_valid():
            team = form.save()
            messages.success(request, f"Team '{team.name}' created successfully.")
            return redirect("organizations:teams")
        return render(request, self.template_name, {"form": form})


class OrganizationMemberListView(OrganizationAccessMixin, ListView):
    """
    Roster of organization employees with filtering and search.
    """
    template_name = "organizations/member_list.html"
    context_object_name = "members"
    paginate_by = 25

    def get_queryset(self):
        qs = OrganizationMember.objects.filter(
            organization=self.request.organization
        ).select_related("user", "department", "branch", "reports_to")

        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                user__email__icontains=query
            ) | qs.filter(
                user__first_name__icontains=query
            ) | qs.filter(
                user__last_name__icontains=query
            ) | qs.filter(
                employee_id__icontains=query
            )
        return qs


class MemberEditView(OrganizationAccessMixin, RoleRequiredMixin, View):
    """
    Edits member details, department, branch, and supervisor line with cycle detection.
    """
    template_name = "organizations/member_form.html"
    required_roles = [SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN]

    def get(self, request, member_id):
        member = get_object_or_404(OrganizationMember, id=member_id, organization=request.organization)
        form = OrganizationMemberForm(instance=member, organization=request.organization)
        return render(request, self.template_name, {"form": form, "member": member})

    def post(self, request, member_id):
        member = get_object_or_404(OrganizationMember, id=member_id, organization=request.organization)
        form = OrganizationMemberForm(request.POST, instance=member, organization=request.organization)
        if form.is_valid():
            new_manager = form.cleaned_data.get("reports_to")
            if new_manager:
                try:
                    HierarchyService.validate_reporting_chain(member, new_manager)
                except ValidationError as err:
                    form.add_error("reports_to", err.message)
                    return render(request, self.template_name, {"form": form, "member": member})

            form.save()
            messages.success(request, f"Membership for {member.user.get_full_name()} updated.")
            return redirect("organizations:members")
        return render(request, self.template_name, {"form": form, "member": member})


class HierarchyTreeView(OrganizationAccessMixin, TemplateView):
    """
    Renders visual organizational chart and reporting structures.
    """
    template_name = "organizations/hierarchy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.organization
        context["department_tree"] = HierarchyService.build_department_tree(org)
        context["top_executives"] = org.members.filter(reports_to__isnull=True, status="ACTIVE").select_related("user")
        return context


class InvitationListView(OrganizationAccessMixin, RoleRequiredMixin, ListView):
    """
    Lists pending, accepted, and expired invitations.
    """
    template_name = "organizations/invitations.html"
    context_object_name = "invitations"
    required_roles = [SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN]

    def get_queryset(self):
        return OrganizationInvitation.objects.filter(
            organization=self.request.organization
        ).select_related("invited_by", "role", "department", "branch")


class InvitationCreateView(OrganizationAccessMixin, RoleRequiredMixin, View):
    """
    Issues a new email invitation to join the organization.
    """
    template_name = "organizations/invitation_form.html"
    required_roles = [SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN]

    def get(self, request):
        form = OrganizationInvitationForm(organization=request.organization)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = OrganizationInvitationForm(request.POST, organization=request.organization)
        if form.is_valid():
            try:
                InvitationService.create_invitation(
                    organization=request.organization,
                    email=form.cleaned_data["email"],
                    invited_by=request.user,
                    role=form.cleaned_data.get("role"),
                    branch=form.cleaned_data.get("branch"),
                    department=form.cleaned_data.get("department"),
                    job_title=form.cleaned_data.get("job_title", ""),
                    request=request,
                )
                messages.success(request, f"Invitation sent to {form.cleaned_data['email']}.")
                return redirect("organizations:invitations")
            except ValidationError as err:
                messages.error(request, err.message)
        return render(request, self.template_name, {"form": form})


class AcceptInvitationView(View):
    """
    Public landing page to accept an invitation token.
    """
    template_name = "organizations/invitation_accept.html"

    def get(self, request, token):
        invitation = OrganizationInvitation.objects.filter(token=token, status="PENDING").first()
        if not invitation or invitation.is_expired:
            messages.error(request, "This invitation token is invalid or has expired.")
            return redirect("accounts:login")
        return render(request, self.template_name, {"invitation": invitation})

    def post(self, request, token):
        invitation = OrganizationInvitation.objects.filter(token=token, status="PENDING").first()
        if not invitation or invitation.is_expired:
            messages.error(request, "This invitation token is invalid or has expired.")
            return redirect("accounts:login")

        # If user is logged in, bind directly
        if request.user.is_authenticated:
            try:
                InvitationService.accept_invitation(token, request.user)
                request.session["active_organization_id"] = str(invitation.organization.id)
                messages.success(request, f"You have successfully joined {invitation.organization.name}!")
                return redirect("organizations:dashboard")
            except ValidationError as err:
                messages.error(request, err.message)
                return redirect("organizations:dashboard")
        else:
            messages.info(request, "Please sign in or register to accept your invitation.")
            return redirect(f"{reverse('accounts:login')}?next={request.path}")


class OrganizationSettingsView(OrganizationAccessMixin, RoleRequiredMixin, View):
    """
    Manages tenant configuration policies.
    """
    template_name = "organizations/settings.html"
    required_roles = [SystemRole.SUPER_ADMIN, SystemRole.ORG_ADMIN]

    def get(self, request):
        config, _ = OrganizationConfiguration.objects.get_or_create(organization=request.organization)
        form = OrganizationConfigurationForm(instance=config)
        return render(request, self.template_name, {"form": form, "config": config})

    def post(self, request):
        config, _ = OrganizationConfiguration.objects.get_or_create(organization=request.organization)
        form = OrganizationConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Organization configuration policies have been updated.")
            return redirect("organizations:settings")
        return render(request, self.template_name, {"form": form, "config": config})
