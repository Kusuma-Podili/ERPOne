from django import forms
from .models import Document, DocumentCategory, DocumentFolder, DocumentTemplate, DocumentComment
class DocumentForm(forms.ModelForm):
    class Meta:
        model=Document; fields=['title','description','category','folder','visibility','tags','expires_at']
class DocumentUploadForm(forms.Form):
    file=forms.FileField(); change_summary=forms.CharField(required=False,widget=forms.Textarea(attrs={'rows':3}))
class CategoryForm(forms.ModelForm):
    class Meta: model=DocumentCategory; fields=['name','code','description','parent','retention_days','requires_approval','is_active']
class FolderForm(forms.ModelForm):
    class Meta: model=DocumentFolder; fields=['name','path','parent']
class TemplateForm(forms.ModelForm):
    class Meta: model=DocumentTemplate; fields=['name','code','description','category','template_body','variables','version','is_active']
class CommentForm(forms.ModelForm):
    class Meta: model=DocumentComment; fields=['body','version']
