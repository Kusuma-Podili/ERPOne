from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404,render,redirect
from .models import *
from .forms import *
from .services import NotificationService
def _org(u): return getattr(u,'organization',None) or getattr(u,'current_organization',None)
@login_required
def inbox(request):
    org=_org(request.user); qs=Notification.objects.filter(organization=org,recipient=request.user); return render(request,'notifications/inbox.html',{'notifications':qs[:100],'unread':qs.filter(is_read=False).count()})
@login_required
def mark_read(request,pk):
    n=get_object_or_404(Notification,pk=pk,recipient=request.user); n.mark_read(); return JsonResponse({'ok':True})
@login_required
def mark_all_read(request):
    qs=Notification.objects.filter(recipient=request.user,is_read=False); from django.utils import timezone; qs.update(is_read=True,read_at=timezone.now()); return redirect('notifications:inbox')
@login_required
def preferences(request):
    org=_org(request.user); form=NotificationPreferenceForm(request.POST or None)
    if request.method=='POST' and form.is_valid(): o=form.save(commit=False); o.organization=org; o.user=request.user; o.save(); return redirect('notifications:preferences')
    return render(request,'notifications/preferences.html',{'form':form,'preferences':NotificationPreference.objects.filter(organization=org,user=request.user)})
@login_required
def templates(request):
    org=_org(request.user); return render(request,'notifications/templates.html',{'templates':NotificationTemplate.objects.filter(organization=org)})
@login_required
def template_create(request):
    org=_org(request.user); form=NotificationTemplateForm(request.POST or None)
    if request.method=='POST' and form.is_valid(): o=form.save(commit=False); o.organization=org; o.save(); return redirect('notifications:templates')
    return render(request,'notifications/form.html',{'form':form,'title':'Notification Template'})
@login_required
def retry_failed(request): return JsonResponse({'retried':NotificationService.retry_failed()})
