from django.db.models import Q
from .models import Document, DocumentAccessLog, DocumentComment, DocumentVersion
class DocumentSearch:
    @staticmethod
    def execute(org, query=None, statuses=None, categories=None, owner=None, folder=None, tag=None, include_archived=False):
        qs=Document.objects.filter(organization=org).select_related("category","folder","owner")
        if query:
            qs=qs.filter(Q(title__icontains=query)|Q(document_number__icontains=query)|Q(description__icontains=query)|Q(tags__icontains=query))
        if statuses: qs=qs.filter(status__in=statuses)
        if categories: qs=qs.filter(category_id__in=categories)
        if owner: qs=qs.filter(owner_id=owner)
        if folder: qs=qs.filter(folder_id=folder)
        if tag: qs=qs.filter(tags__icontains=tag)
        if not include_archived: qs=qs.exclude(status="archived")
        return qs.order_by("-updated_at")
    @staticmethod
    def recent_access(org, limit=50): return DocumentAccessLog.objects.filter(organization=org).select_related("document","user")[:limit]
    @staticmethod
    def versions(document): return DocumentVersion.objects.filter(document=document).select_related("uploaded_by").order_by("-version")
    @staticmethod
    def unresolved_comments(document): return DocumentComment.objects.filter(document=document,is_resolved=False).select_related("author")
    @staticmethod
    def facets(org):
        return {"categories":list(Document.objects.filter(organization=org,category__isnull=False).values("category__id","category__name").distinct()),"statuses":list(Document.objects.filter(organization=org).values("status").distinct()),"owners":list(Document.objects.filter(organization=org,owner__isnull=False).values("owner__id","owner__email").distinct())}
