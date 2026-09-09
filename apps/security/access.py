"""Access governance helpers for least privilege and periodic review."""
from collections import defaultdict
from django.utils import timezone
from .models import AccessReviewItem,RolePermissionSet,SecurityPolicy

class LeastPrivilegeAnalyzer:
    def __init__(self,user): self.user=user
    def permissions(self): return sorted(self.user.get_permissions_list())
    def unused_candidates(self,used_permissions): return [p for p in self.permissions() if p not in set(used_permissions)]
    def high_value_permissions(self):
        markers=("admin","delete","export","approve","security","payroll","finance")
        return [p for p in self.permissions() if any(m in p.lower() for m in markers)]
    def recommendation(self,used_permissions=()):
        unused=self.unused_candidates(used_permissions); privileged=self.high_value_permissions(); return {"user":str(self.user.pk),"permission_count":len(self.permissions()),"unused_candidates":unused,"privileged_permissions":privileged,"recommendation":"REVIEW" if unused or len(privileged)>5 else "NORMAL"}

class PermissionSetService:
    @staticmethod
    def effective(sets):
        result=set()
        for item in sets: result.update(item.permissions or [])
        return sorted(result)
    @staticmethod
    def conflicts(sets):
        mapping=defaultdict(list)
        for item in sets:
            for perm in item.permissions or []: mapping[perm].append(item.code)
        return {p:owners for p,owners in mapping.items() if len(owners)>1}
    @staticmethod
    def validate_permissions(permissions,allowed): return sorted(set(permissions)-set(allowed))

class ReviewDecisionService:
    @staticmethod
    def pending(review): return review.items.filter(decision="PENDING")
    @staticmethod
    def revocations(review): return review.items.filter(decision="REVOKE")
    @staticmethod
    def modifications(review): return review.items.filter(decision="MODIFY")
    @staticmethod
    def completion(review):
        total=review.items.count(); pending=ReviewDecisionService.pending(review).count(); return {"total":total,"pending":pending,"completed":total-pending,"percent":round((total-pending)/total*100,2) if total else 100}
    @staticmethod
    def overdue(review): return bool(review.due_at and review.due_at<timezone.now() and review.status not in {"COMPLETED","CANCELLED"})
