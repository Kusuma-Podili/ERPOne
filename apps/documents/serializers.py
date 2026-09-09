from rest_framework import serializers
from .models import Document,DocumentVersion,DocumentComment,DocumentPermission
class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta: model=DocumentVersion; fields=["id","version","original_filename","mime_type","file_size","checksum","change_summary","created_at","is_current"]
class DocumentSerializer(serializers.ModelSerializer):
    versions=DocumentVersionSerializer(many=True,read_only=True)
    class Meta: model=Document; fields=["id","document_number","title","description","category","folder","owner","status","visibility","tags","metadata","current_version","expires_at","created_at","updated_at","versions"]
class DocumentCommentSerializer(serializers.ModelSerializer):
    class Meta: model=DocumentComment; fields="__all__"
class DocumentPermissionSerializer(serializers.ModelSerializer):
    class Meta: model=DocumentPermission; fields="__all__"
