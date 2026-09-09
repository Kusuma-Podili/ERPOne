from django.db import transaction
from .models import DocumentApproval, DocumentApprovalStep, ApprovalStatus, DocumentStatus
from .services import DocumentService
class ApprovalEngine:
    @staticmethod
    def ordered(document): return document.approvals.select_related("step","approver").order_by("step__sequence","created_at")
    @staticmethod
    def can_decide(approval,user):
        if approval.status!=ApprovalStatus.PENDING: return False
        if approval.step and approval.step.approver_user_id: return approval.step.approver_user_id==user.pk
        return approval.approver_id in (None,user.pk)
    @staticmethod
    @transaction.atomic
    def approve(approval,user,comments=""):
        if not ApprovalEngine.can_decide(approval,user): raise PermissionError("Approval is not assigned to this user")
        return DocumentService.decide(approval,user,ApprovalStatus.APPROVED,comments)
    @staticmethod
    @transaction.atomic
    def reject(approval,user,comments=""):
        if not ApprovalEngine.can_decide(approval,user): raise PermissionError("Approval is not assigned to this user")
        return DocumentService.decide(approval,user,ApprovalStatus.REJECTED,comments)
    @staticmethod
    def progress(document):
        all_steps=document.approvals.count(); approved=document.approvals.filter(status=ApprovalStatus.APPROVED).count(); rejected=document.approvals.filter(status=ApprovalStatus.REJECTED).count(); return {"total":all_steps,"approved":approved,"rejected":rejected,"pending":max(0,all_steps-approved-rejected),"percent":round(approved/all_steps*100,2) if all_steps else 0}
