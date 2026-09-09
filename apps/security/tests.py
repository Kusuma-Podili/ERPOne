from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization
from .models import SecurityPolicy, SecurityEvent, SecurityIncident, UserSession
from .services import MFAService, PolicyEngine, RiskAssessmentService, AuditService, SessionSecurityService, IncidentService

class SecurityServiceTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(email="security@example.com",password="StrongPassword123!",first_name="Security",last_name="Tester")
        self.org=Organization.objects.create(name="Security Org",slug="security-org",code="SEC")
    def test_policy_ip_allowlist(self):
        SecurityPolicy.objects.create(organization=self.org,name="Default",code="default",ip_allowlist=["10.0.0.0/8"])
        self.assertTrue(PolicyEngine.ip_allowed(self.org,"10.1.2.3")); self.assertFalse(PolicyEngine.ip_allowed(self.org,"8.8.8.8"))
    def test_mfa_round_trip(self):
        challenge,code=MFAService.issue(self.user); self.assertTrue(MFAService.verify(challenge,code)); self.assertEqual(challenge.status,"VERIFIED")
    def test_risk(self): self.assertEqual(RiskAssessmentService.residual(80,50),40)
    def test_audit_diff(self):
        e=AuditService.record(actor=self.user,organization=self.org,action="UPDATE",instance=self.user,before={"name":"A"},after={"name":"B"}); self.assertEqual(e.changed_fields,["name"])
    def test_session_revoke(self):
        s=UserSession.objects.create(user=self.user,session_key="abc123"); SessionSecurityService.revoke("abc123"); s.refresh_from_db(); self.assertEqual(s.status,"REVOKED")
    def test_incident_transition(self):
        i=IncidentService.create(self.org,"Test","Desc","AUTH"); IncidentService.transition(i,"INVESTIGATING",self.user); i.refresh_from_db(); self.assertEqual(i.status,"INVESTIGATING")
