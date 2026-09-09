from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import *
class DocumentService:
    @staticmethod
    @transaction.atomic
    def add_version(document, uploaded_file, user, summary=''):
        latest=document.versions.order_by('-version').first(); number=(latest.version+1 if latest else 1)
        DocumentVersion.objects.filter(document=document,is_current=True).update(is_current=False)
        v=DocumentVersion.objects.create(document=document,version=number,file=uploaded_file,original_filename=getattr(uploaded_file,'name','document'),file_size=getattr(uploaded_file,'size',0),uploaded_by=user,change_summary=summary,is_current=True)
        try: v.calculate_checksum(); v.save(update_fields=['checksum'])
        except Exception: pass
        document.current_version=number; document.status=DocumentStatus.PENDING if document.category_id and document.category.requires_approval else DocumentStatus.APPROVED; document.save(update_fields=['current_version','status','updated_at'])
        DocumentAccessLog.objects.create(organization=document.organization,document=document,user=user,action='upload',details={'version':number})
        return v
    @staticmethod
    def permission(document,user,action='view'):
        if document.owner_id==getattr(user,'pk',None): return True
        if document.visibility==DocumentVisibility.ORGANIZATION and getattr(user,'is_authenticated',False): return True
        p=document.permissions.filter(user=user).first()
        return bool(p and p.active() and getattr(p,'can_'+action,False))
    @staticmethod
    def decide(approval, user, status, comments=''):
        approval.status=status; approval.approver=user; approval.comments=comments; approval.decided_at=timezone.now(); approval.save()
        doc=approval.document
        if status==ApprovalStatus.REJECTED: doc.status=DocumentStatus.REJECTED
        elif status==ApprovalStatus.APPROVED:
            pending=doc.approvals.filter(status=ApprovalStatus.PENDING).exclude(pk=approval.pk).exists(); doc.status=DocumentStatus.PENDING if pending else DocumentStatus.APPROVED
        doc.save(update_fields=['status','updated_at']); DocumentAccessLog.objects.create(organization=doc.organization,document=doc,user=user,action='approve' if status==ApprovalStatus.APPROVED else 'reject',details={'approval':str(approval.pk)})
        return doc
    @staticmethod
    def archive(document,user):
        document.status=DocumentStatus.ARCHIVED; document.archived_at=timezone.now(); document.save(update_fields=['status','archived_at','updated_at']); DocumentAccessLog.objects.create(organization=document.organization,document=document,user=user,action='archive')
    @staticmethod
    def retention_scan(org):
        now=timezone.now(); events=DocumentRetentionEvent.objects.filter(document__organization=org,success=False,scheduled_for__lte=now)
        done=0
        for e in events:
            try:
                if e.event_type=='archive': DocumentService.archive(e.document,None)
                elif e.event_type=='expire': e.document.status=DocumentStatus.EXPIRED; e.document.save(update_fields=['status','updated_at'])
                e.success=True; e.executed_at=now; e.save(update_fields=['success','executed_at']); done+=1
            except Exception: pass
        return done
    @staticmethod
    def search(org,query='',category=None,status=None):
        qs=Document.objects.filter(organization=org).select_related('category','folder','owner')
        if query: qs=qs.filter(title__icontains=query)|Document.objects.filter(organization=org,description__icontains=query)
        if category: qs=qs.filter(category_id=category)
        if status: qs=qs.filter(status=status)
        return qs.distinct()
class DocumentWorkflowService:
    @staticmethod
    def start(document,workflow,user):
        document.status=DocumentStatus.PENDING; document.save(update_fields=['status','updated_at'])
        created=[]
        for step in workflow.steps.all(): created.append(DocumentApproval.objects.create(document=document,workflow=workflow,step=step,approver=step.approver_user,status=ApprovalStatus.PENDING))
        return created
    @staticmethod
    def next_pending(document): return document.approvals.filter(status=ApprovalStatus.PENDING).order_by('step__sequence').first()
