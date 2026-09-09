import csv
from io import StringIO
from .models import Document,DocumentVersion
class DocumentExporter:
    @staticmethod
    def csv(queryset):
        out=StringIO(); w=csv.writer(out); w.writerow(["Number","Title","Status","Category","Owner","Version","Updated"])
        for d in queryset.select_related("category","owner"): w.writerow([d.document_number,d.title,d.status,d.category.name if d.category else "",d.owner.email if d.owner else "",d.current_version,d.updated_at.isoformat()])
        return out.getvalue()
    @staticmethod
    def version_manifest(document):
        return [{"version":v.version,"filename":v.original_filename,"size":v.file_size,"checksum":v.checksum,"uploaded_at":v.created_at.isoformat()} for v in document.versions.all()]
