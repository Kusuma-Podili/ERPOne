from datetime import timedelta
from django.db.models import Count
from django.utils import timezone
from .models import NotificationDelivery,DeliveryStatus
from .services import NotificationService
class DeliveryManager:
    @staticmethod
    def queue(notification,channels):
        return [NotificationDelivery.objects.get_or_create(notification=notification,channel=c)[0] for c in channels]
    @staticmethod
    def process(limit=100):
        qs=NotificationDelivery.objects.filter(status=DeliveryStatus.QUEUED).order_by("queued_at")[:limit]; return sum(NotificationService.send_delivery(d) for d in qs)
    @staticmethod
    def retry(limit=100): return NotificationService.retry_failed(limit)
    @staticmethod
    def health():
        rows=NotificationDelivery.objects.values("status").annotate(count=Count("id")); return {r["status"]:r["count"] for r in rows}
    @staticmethod
    def stale(minutes=30): return NotificationDelivery.objects.filter(status=DeliveryStatus.QUEUED,queued_at__lt=timezone.now()-timedelta(minutes=minutes))
