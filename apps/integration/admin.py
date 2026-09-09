from django.contrib import admin
from .models import *
for model in [IntegrationConnection,IntegrationEndpoint,IntegrationMapping,IntegrationJob,IntegrationJobRun,IntegrationEvent,IntegrationDelivery,DeadLetterEvent,SyncCursor,ReconciliationRun,ReconciliationItem,FeatureFlag,SystemConfiguration,ReleaseRecord,ReleaseCheck,DataMigrationRun,IntegrationAuditEvent]:
    admin.site.register(model)
