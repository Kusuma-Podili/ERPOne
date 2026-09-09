from django.contrib import admin
from .models import *
for model in [DocumentCategory,DocumentFolder,Document,DocumentVersion,DocumentPermission,DocumentShare,DocumentApprovalWorkflow,DocumentApprovalStep,DocumentApproval,DocumentComment,DocumentTag,DocumentAccessLog,DocumentRetentionPolicy,DocumentRetentionEvent,DocumentTemplate]:
    admin.site.register(model)
