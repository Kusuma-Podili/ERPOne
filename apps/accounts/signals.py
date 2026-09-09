"""
Accounts Signals.
Automates profile instantiation, default role assignment, and audit event triggers.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User, UserProfile, Role, UserRole
from enterpriseone.configuration.roles import SystemRole


@receiver(post_save, sender=User)
def handle_user_post_save(sender, instance: User, created: bool, **kwargs):
    """
    Ensures every created user has an associated UserProfile and a foundational role.
    """
    if created:
        # Create UserProfile if it does not already exist
        UserProfile.objects.get_or_create(user=instance)

        # Default role assignment
        if instance.is_superuser:
            role_code = SystemRole.SUPER_ADMIN
        else:
            role_code = SystemRole.EMPLOYEE

        role = Role.objects.filter(code=role_code).first()
        if role and not UserRole.objects.filter(user=instance).exists():
            UserRole.objects.create(user=instance, role=role)
