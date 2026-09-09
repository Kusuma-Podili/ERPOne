from django.contrib import admin
from .models import *
for model in [NotificationTemplate,NotificationPreference,Notification,NotificationDelivery,NotificationBatch,Reminder,ScheduledNotification,NotificationRule,EventSubscription,UserNotificationDigest,NotificationAuditEvent]:
    admin.site.register(model)
