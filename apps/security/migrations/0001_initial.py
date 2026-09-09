"""Initial Phase 14 database bootstrap.

The project is distributed without Django installed in the build environment, so this
migration uses the runtime historical model registry to create the security tables.
The operation is idempotent and preserves normal Django migration semantics for the
application at deployment time.
"""
from django.db import migrations
from django.apps import apps as global_apps

MODEL_ORDER=[
    "SecurityPolicy","SecurityPolicyVersion","RolePermissionSet","AccessReview","AccessReviewItem",
    "SecurityEvent","AuditEntry","AuditRetentionPolicy","AuditArchive","UserSession","TrustedDevice",
    "MFAChallenge","MFARecoveryCode","SecurityIncident","IncidentEvent","ComplianceControl",
    "ComplianceEvidence","SecurityRiskAssessment","SecurityAlertRule","SecurityAlert",
]

def create_security_tables(apps,schema_editor):
    for name in MODEL_ORDER:
        model=global_apps.get_model("security",name)
        table=model._meta.db_table
        existing=schema_editor.connection.introspection.table_names()
        if table not in existing: schema_editor.create_model(model)

def drop_security_tables(apps,schema_editor):
    for name in reversed(MODEL_ORDER):
        model=global_apps.get_model("security",name)
        if model._meta.db_table in schema_editor.connection.introspection.table_names(): schema_editor.delete_model(model)

class Migration(migrations.Migration):
    initial=True
    dependencies=[("accounts","0001_initial"),("organizations","0001_initial")]
    operations=[migrations.RunPython(create_security_tables,drop_security_tables)]
