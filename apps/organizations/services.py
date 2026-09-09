"""
Organizations Domain Services Layer.
Encapsulates business operations for Organization Provisioning, Hierarchy Traversal, Reporting Cycles, and Invitations.
"""
import uuid
from datetime import timedelta
from typing import Optional, List, Dict, Any
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User, Role
from apps.accounts.services import RBACService
from enterpriseone.configuration.roles import SystemRole
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


class OrganizationService:
    """
    Coordinates tenant creation, provisioning of initial branches, HQ facilities, and configuration policies.
    """

    @classmethod
    def create_organization(
        cls,
        name: str,
        code: str,
        slug: Optional[str] = None,
        currency: str = "USD",
        creator: Optional[User] = None,
        hq_name: str = "Corporate Headquarters",
        hq_city: str = "New York",
        hq_country: str = "United States",
    ) -> Organization:
        """
        Provisions a complete enterprise organization with default configuration, HQ location,
        main branch, standard departments, and assigns creator as Organization Administrator.
        """
        if not slug:
            slug = slugify(name)

        # 1. Create Organization & Configuration
        org = Organization.objects.create(
            name=name,
            code=code.upper().strip(),
            slug=slug,
            currency=currency,
        )
        OrganizationConfiguration.objects.create(organization=org)

        # 2. Create Default Headquarters Location
        hq_location = Location.objects.create(
            organization=org,
            name=hq_name,
            code="HQ-01",
            address_line1="100 Enterprise Way",
            city=hq_city,
            country=hq_country,
            is_headquarters=True,
        )

        # 3. Create Main Branch
        main_branch = Branch.objects.create(
            organization=org,
            name=f"{name} Main Branch",
            code="BR-01",
            location=hq_location,
            manager=creator,
        )

        # 4. Create Standard Department Baseline
        standard_depts = [
            ("Executive Leadership", "EXEC", "Executive division"),
            ("Human Resources", "HR", "Personnel and talent acquisition"),
            ("Finance & Accounting", "FIN", "Financial ledger and fiscal oversight"),
            ("Sales & Marketing", "SALES", "Customer acquisition and pipeline"),
            ("Supply Chain & Operations", "OPS", "Logistics and inventory management"),
        ]
        for dept_name, dept_code, desc in standard_depts:
            Department.objects.create(
                organization=org,
                branch=main_branch,
                name=dept_name,
                code=dept_code,
                description=desc,
            )

        # 5. Bind Creator as Organization Administrator
        if creator:
            member = OrganizationMember.objects.create(
                organization=org,
                user=creator,
                branch=main_branch,
                job_title="Managing Director",
                is_org_admin=True,
            )
            # Assign ORG_ADMIN system role
            org_admin_role = Role.objects.filter(code=SystemRole.ORG_ADMIN).first()
            if org_admin_role:
                RBACService.assign_role_to_user(creator, org_admin_role, assigned_by=creator)

        return org


class HierarchyService:
    """
    Manages recursive organizational trees, reporting lines, and circular relationship prevention.
    """

    @classmethod
    def validate_reporting_chain(cls, member: OrganizationMember, new_manager: User):
        """
        Detects circular reporting loops: Prevents member from reporting to someone
        who directly or indirectly reports back to member.
        """
        if member.user_id == new_manager.id:
            raise ValidationError("An employee cannot report to themselves.")

        # Traverse up the reporting chain of new_manager
        current_user = new_manager
        visited = set()

        while current_user:
            if current_user.id in visited:
                break
            visited.add(current_user.id)

            if current_user.id == member.user_id:
                raise ValidationError(
                    f"Circular hierarchy detected: {new_manager.get_full_name()} is in the direct reporting line of {member.user.get_full_name()}."
                )

            # Find who current_user reports to in this organization
            mgr_membership = OrganizationMember.objects.filter(
                organization=member.organization, user=current_user
            ).first()
            current_user = mgr_membership.reports_to if mgr_membership else None

    @classmethod
    def get_direct_and_indirect_reports(cls, organization: Organization, manager_user: User) -> List[User]:
        """
        Retrieves all downstream subordinates of a manager across all hierarchy levels.
        """
        reports = []
        queue = [manager_user]
        visited = set()

        while queue:
            curr = queue.pop(0)
            if curr.id in visited:
                continue
            visited.add(curr.id)

            subordinates = OrganizationMember.objects.filter(
                organization=organization, reports_to=curr
            ).select_related("user")

            for sub in subordinates:
                reports.append(sub.user)
                queue.append(sub.user)

        return reports

    @classmethod
    def build_department_tree(cls, organization: Organization) -> List[Dict[str, Any]]:
        """
        Constructs recursive nested tree structure of departments for UI visualizer.
        """
        all_depts = list(organization.departments.select_related("head_of_department", "branch").all())
        dept_map = {d.id: {"dept": d, "children": []} for d in all_depts}
        tree = []

        for d in all_depts:
            if d.parent_department_id and d.parent_department_id in dept_map:
                dept_map[d.parent_department_id]["children"].append(dept_map[d.id])
            else:
                tree.append(dept_map[d.id])

        return tree


class InvitationService:
    """
    Manages creation, HMAC tokenization, email distribution, and acceptance of organization invitations.
    """
    SIGNER_SALT = "enterpriseone-org-invitation-salt"

    @classmethod
    def create_invitation(
        cls,
        organization: Organization,
        email: str,
        invited_by: Optional[User] = None,
        role: Optional[Role] = None,
        department: Optional[Department] = None,
        branch: Optional[Branch] = None,
        job_title: str = "",
        expires_days: int = 7,
        request=None,
    ) -> OrganizationInvitation:
        """
        Creates an invitation with a tamper-resistant token and sends onboarding email.
        """
        email = email.strip().lower()

        # Check if already an active member
        existing_member = OrganizationMember.objects.filter(
            organization=organization, user__email__iexact=email, status="ACTIVE"
        ).exists()
        if existing_member:
            raise ValidationError(f"A user with email {email} is already an active member of this organization.")

        signer = TimestampSigner(salt=cls.SIGNER_SALT)
        token = signer.sign(f"{organization.id}:{email}:{uuid.uuid4().hex[:8]}")

        invitation = OrganizationInvitation.objects.create(
            organization=organization,
            email=email,
            invited_by=invited_by,
            role=role,
            department=department,
            branch=branch,
            job_title=job_title,
            token=token,
            expires_at=timezone.now() + timedelta(days=expires_days),
            status="PENDING",
        )

        cls.send_invitation_email(invitation, request)
        return invitation

    @classmethod
    def send_invitation_email(cls, invitation: OrganizationInvitation, request=None):
        """Dispatches invitation email with activation link."""
        base_url = (
            request.build_absolute_uri("/").rstrip("/")
            if request
            else "http://localhost:8000"
        )
        accept_url = f"{base_url}/organizations/invitations/{invitation.token}/accept/"

        subject = f"Invitation to join {invitation.organization.name} on EnterpriseOne"
        message = (
            f"Hello,\n\n"
            f"You have been invited to join {invitation.organization.name} on EnterpriseOne as {invitation.job_title or 'a Team Member'}.\n\n"
            f"Click the link below to accept your invitation:\n"
            f"{accept_url}\n\n"
            f"This invitation will expire on {invitation.expires_at:%B %d, %Y}.\n\n"
            f"— The {invitation.organization.name} Administrative Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                fail_silently=True,
            )
        except Exception:
            pass

    @classmethod
    def accept_invitation(cls, token: str, user: User) -> OrganizationMember:
        """
        Validates token, ensures expiry has not passed, and provisions OrganizationMember.
        """
        invitation = OrganizationInvitation.objects.filter(token=token, status="PENDING").first()
        if not invitation:
            raise ValidationError("This invitation token is invalid or has already been used.")

        if invitation.is_expired:
            invitation.status = "EXPIRED"
            invitation.save(update_fields=["status"])
            raise ValidationError("This invitation has expired. Please request a new invitation.")

        # Create or update membership
        member, _ = OrganizationMember.objects.update_or_create(
            organization=invitation.organization,
            user=user,
            defaults={
                "branch": invitation.branch,
                "department": invitation.department,
                "job_title": invitation.job_title,
                "status": "ACTIVE",
            },
        )

        # Assign role if specified
        if invitation.role:
            RBACService.assign_role_to_user(user, invitation.role, assigned_by=invitation.invited_by)

        invitation.status = "ACCEPTED"
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_at"])

        return member
