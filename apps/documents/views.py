from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models import *
from .forms import *
from .services import DocumentService, DocumentWorkflowService
def _org(u): return getattr(u,'organization',None) or getattr(u,'current_organization',None)
@login_required
def dashboard(request):
    org=_org(request.user); qs=Document.objects.filter(organization=org) if org else Document.objects.none(); return render(request,'documents/dashboard.html',{'documents':qs[:25],'counts':{'total':qs.count(),'pending':qs.filter(status='pending').count(),'approved':qs.filter(status='approved').count(),'archived':qs.filter(status='archived').count()}})
@login_required
def document_list(request):
    org=_org(request.user); qs=DocumentService.search(org,request.GET.get('q',''),request.GET.get('category'),request.GET.get('status')); return render(request,'documents/list.html',{'documents':qs[:200],'query':request.GET.get('q','')})
@login_required
def document_create(request):
    org=_org(request.user); form=DocumentForm(request.POST or None)
    if request.method=='POST' and form.is_valid(): obj=form.save(commit=False); obj.organization=org; obj.owner=request.user; obj.save(); messages.success(request,'Document created.'); return redirect('documents:detail',obj.pk)
    return render(request,'documents/form.html',{'form':form,'title':'Create Document'})
@login_required
def detail(request,pk):
    org=_org(request.user); obj=get_object_or_404(Document,pk=pk,organization=org); return render(request,'documents/detail.html',{'document':obj,'versions':obj.versions.all(),'comments':obj.comments.filter(parent__isnull=True)})
@login_required
def upload_version(request,pk):
    org=_org(request.user); obj=get_object_or_404(Document,pk=pk,organization=org); form=DocumentUploadForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid(): DocumentService.add_version(obj,form.cleaned_data['file'],request.user,form.cleaned_data['change_summary']); return redirect('documents:detail',pk)
    return render(request,'documents/form.html',{'form':form,'title':'Upload Version'})
@login_required
def download(request,pk,version=None):
    org=_org(request.user); doc=get_object_or_404(Document,pk=pk,organization=org)
    if not DocumentService.permission(doc,request.user,'download'): raise Http404('Download permission denied')
    v=get_object_or_404(doc.versions,version=version or doc.current_version); DocumentAccessLog.objects.create(organization=org,document=doc,user=request.user,action='download',details={'version':v.version}); return redirect(v.file.url)
@login_required
def approve(request,pk):
    org=_org(request.user); doc=get_object_or_404(Document,pk=pk,organization=org); approval=DocumentWorkflowService.next_pending(doc)
    if not approval: return JsonResponse({'status':'no_pending_approval'})
    DocumentService.decide(approval,request.user,ApprovalStatus.APPROVED,request.POST.get('comments','')); return JsonResponse({'status':'approved','document_status':doc.status})
@login_required
def archive(request,pk):
    org=_org(request.user); doc=get_object_or_404(Document,pk=pk,organization=org); DocumentService.archive(doc,request.user); return redirect('documents:detail',pk)
