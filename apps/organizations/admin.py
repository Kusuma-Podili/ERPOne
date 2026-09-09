"""
Django Administration Configuration for Organizations.
Provides administrative interfaces for Organization, Location, Branch, Department, Team, and Members.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
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


class OrganizationConfigurationInline(admin.StackedInline):
    model = OrganizationConfiguration
    can_delete = False
    verbose_name_plural = "Configuration Policies"


class LocationInline(admin.TabularInline):
    model = Location
    extra = 1
    fields = ("name", "code", "city", "country", "is_headquarters", "is_active")


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 1
    fields = ("name", "code", "location", "manager", "is_active")


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1
    fields = ("name", "code", "branch", "parent_department", "head_of_department", "is_active")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug", "currency", "is_active", "created_at")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "code", "registration_number", "tax_id")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OrganizationConfigurationInline, LocationInline, BranchInline]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "city", "country", "is_headquarters", "is_active")
    list_filter = ("organization", "is_headquarters", "is_active", "country")
    search_fields = ("name", "code", "city", "postal_code")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "location", "manager", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code")
    inlines = [DepartmentInline]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "branch", "parent_department", "head_of_department", "is_active")
    list_filter = ("organization", "branch", "is_active")
    search_fields = ("name", "code", "budget_code")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "department", "team_lead", "is_active")
    list_filter = ("department__organization", "is_active")
    search_fields = ("name", "code")


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "branch", "department", "job_title", "is_org_admin", "status")
    list_filter = ("organization", "branch", "department", "is_org_admin", "status")
    search_fields = ("user__email", "user__first_name", "user__last_name", "employee_id", "job_title")


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "member", "role_in_team", "assigned_at")
    list_filter = ("team__department__organization", "role_in_team")
    search_fields = ("member__user__email", "team__name")


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "role", "department", "status", "expires_at", "created_at")
    list_filter = ("organization", "status")
    search_fields = ("email", "organization__name")
    readonly_fields = ("token", "created_at", "accepted_at")
