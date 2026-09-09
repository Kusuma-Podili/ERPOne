"""
Integration Tests for Organization User Invitation Flows.
"""
from datetime import timedelta
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, Role
from apps.organizations.models import Organization, OrganizationInvitation, OrganizationMember
from apps.organizations.services import OrganizationService, InvitationService
from enterpriseone.configuration.roles import SystemRole


class InvitationFlowsTestCase(TestCase):
    """
    Validates email invitations, token expiration, acceptance lifecycle, and role assignment.
    """

    def setUp(self):
        self.client = Client()
        Role.objects.create(code=SystemRole.SUPER_ADMIN, name="Super Admin", priority=100, is_system_role=True)
        self.role_sales = Role.objects.create(code=SystemRole.SALES_USER, name="Sales User", priority=30, is_system_role=True)
        Role.objects.create(code=SystemRole.EMPLOYEE, name="Employee", priority=10, is_system_role=True)

        self.admin_user = User.objects.create_user(
            email="admin@apex.internal",
            password="EnterprisePassword123!",
            first_name="Admin",
            last_name="Person",
        )
        self.invitee_user = User.objects.create_user(
            email="candidate@external.com",
            password="CandidatePassword123!",
            first_name="Candidate",
            last_name="User",
        )
        self.org = OrganizationService.create_organization(
            name="Apex Global",
            code="APEX",
            slug="apex-global",
            creator=self.admin_user,
        )

    def test_create_and_send_invitation_flow(self):
        invitation = InvitationService.create_invitation(
            organization=self.org,
            email="newhire@company.com",
            invited_by=self.admin_user,
            role=self.role_sales,
            job_title="Account Executive",
        )
        self.assertEqual(invitation.status, "PENDING")
        self.assertEqual(invitation.email, "newhire@company.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Invitation to join Apex Global", mail.outbox[0].subject)
        self.assertIn(invitation.token, mail.outbox[0].body)

    def test_inviting_existing_member_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            InvitationService.create_invitation(
                organization=self.org,
                email="admin@apex.internal",  # Already a member
                invited_by=self.admin_user,
            )
        self.assertIn("already an active member", str(ctx.exception))

    def test_accept_invitation_lifecycle(self):
        invitation = InvitationService.create_invitation(
            organization=self.org,
            email="candidate@external.com",
            invited_by=self.admin_user,
            role=self.role_sales,
            job_title="Regional Sales Representative",
        )

        # Candidate logs in and accepts
        self.client.login(username="candidate@external.com", password="CandidatePassword123!")
        accept_url = reverse("organizations:invitation_accept", kwargs={"token": invitation.token})

        # GET landing page
        get_response = self.client.get(accept_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "Apex Global")

        # POST accept
        post_response = self.client.post(accept_url, follow=True)
        self.assertEqual(post_response.status_code, 200)

        # Verify membership and role
        self.assertTrue(
            OrganizationMember.objects.filter(
                organization=self.org, user=self.invitee_user, status="ACTIVE"
            ).exists()
        )
        member = OrganizationMember.objects.get(organization=self.org, user=self.invitee_user)
        self.assertEqual(member.job_title, "Regional Sales Representative")
        self.assertTrue(self.invitee_user.has_role(SystemRole.SALES_USER))

        # Verify invitation status
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "ACCEPTED")
        self.assertIsNotNone(invitation.accepted_at)

    def test_expired_invitation_rejection(self):
        invitation = InvitationService.create_invitation(
            organization=self.org,
            email="candidate@external.com",
            invited_by=self.admin_user,
        )
        # Fast-forward expiration
        invitation.expires_at = timezone.now() - timedelta(days=1)
        invitation.save()

        with self.assertRaises(ValidationError) as ctx:
            InvitationService.accept_invitation(invitation.token, self.invitee_user)
        self.assertIn("invitation has expired", str(ctx.exception))
