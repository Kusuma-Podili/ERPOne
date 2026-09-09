"""Application-facing maintenance orchestration without requiring a task queue."""
from .services import SessionSecurityService, MFAService, RetentionService
from .models import SecurityPolicy

class SecurityMaintenance:
    def run(self,organization=None):
        return {"expired_sessions":SessionSecurityService.expire_stale(),"expired_mfa":self.expire_mfa(),"archived_audit":RetentionService.archive_expired(organization)}
    @staticmethod
    def expire_mfa():
        from django.utils import timezone
        from .models import MFAChallenge
        return MFAChallenge.objects.filter(status="PENDING",expires_at__lt=timezone.now()).update(status="EXPIRED")
    @staticmethod
    def policy_inventory(organization):
        return list(SecurityPolicy.objects.filter(organization=organization).values("name","code","is_active","require_mfa","updated_at"))
