from datetime import timedelta
from django.utils import timezone
from .models import Notification,UserNotificationDigest
class DigestService:
    @staticmethod
    def build(org,user,hours=24):
        end=timezone.now(); start=end-timedelta(hours=hours); ns=Notification.objects.filter(organization=org,recipient=user,created_at__gte=start,created_at__lt=end).order_by("created_at"); d=UserNotificationDigest.objects.create(organization=org,user=user,period_start=start,period_end=end,notification_ids=[str(x.pk) for x in ns],generated_at=end); return d
    @staticmethod
    def render(digest):
        notifications=Notification.objects.filter(id__in=digest.notification_ids).order_by("created_at"); return "\n".join(f"{n.title}: {n.message}" for n in notifications)
    @staticmethod
    def mark_sent(digest): digest.status="sent"; digest.sent_at=timezone.now(); digest.save(update_fields=["status","sent_at"]); return digest
