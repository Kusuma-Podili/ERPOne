from datetime import timedelta
from django.utils import timezone
from .models import MFAChallenge, UserSession, SecurityEvent, SecurityAlertRule
from .services import SessionSecurityService, RetentionService, AlertEngine

def expire_security_sessions():
    return SessionSecurityService.expire_stale()

def expire_mfa_challenges():
    return MFAChallenge.objects.filter(status="PENDING",expires_at__lt=timezone.now()).update(status="EXPIRED")

def purge_or_archive_audit(organization=None):
    return RetentionService.archive_expired(organization)

def evaluate_recent_events(organization,minutes=15):
    cutoff=timezone.now()-timedelta(minutes=minutes); events=SecurityEvent.objects.filter(organization=organization,occurred_at__gte=cutoff); count=0
    for event in events: count += len(AlertEngine.evaluate(event))
    return count
