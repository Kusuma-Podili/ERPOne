from rest_framework import serializers
from .models import Notification,NotificationDelivery,NotificationPreference,Reminder
class NotificationSerializer(serializers.ModelSerializer):
    class Meta: model=Notification; fields="__all__"
class NotificationDeliverySerializer(serializers.ModelSerializer):
    class Meta: model=NotificationDelivery; fields="__all__"
class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta: model=NotificationPreference; fields="__all__"
class ReminderSerializer(serializers.ModelSerializer):
    class Meta: model=Reminder; fields="__all__"
