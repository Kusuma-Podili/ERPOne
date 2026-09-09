from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import ConnectionForm, JobForm, ReleaseForm
from .models import *
from .services import FinalizationReport, HealthReadiness, ReleaseGate
@login_required
def dashboard(request):
    return render(request,"integration/dashboard.html",{"report":FinalizationReport.build(),"recent_events":IntegrationEvent.objects.all()[:12],"dead_letters":DeadLetterEvent.objects.filter(resolved=False)[:8]})
@login_required
def connection_create(request):
    form=ConnectionForm(request.POST or None)
    if form.is_valid(): form.save(); messages.success(request,"Integration connection created."); return redirect("integration:dashboard")
    return render(request,"integration/form.html",{"form":form,"title":"New integration connection"})
@login_required
def job_create(request):
    form=JobForm(request.POST or None)
    if form.is_valid(): form.save(); messages.success(request,"Integration job created."); return redirect("integration:dashboard")
    return render(request,"integration/form.html",{"form":form,"title":"New integration job"})
@login_required
def release_create(request):
    form=ReleaseForm(request.POST or None)
    if form.is_valid(): form.save(); messages.success(request,"Release record created."); return redirect("integration:releases")
    return render(request,"integration/form.html",{"form":form,"title":"New release"})
@login_required
def releases(request): return render(request,"integration/releases.html",{"releases":ReleaseRecord.objects.all()})
@login_required
def release_evaluate(request,pk):
    release=get_object_or_404(ReleaseRecord,pk=pk); passed=ReleaseGate.evaluate(release); messages.success(request,"Release gate passed." if passed else "Release blocked: required checks are incomplete."); return redirect("integration:releases")
@login_required
def dead_letters(request): return render(request,"integration/dead_letters.html",{"items":DeadLetterEvent.objects.filter(resolved=False)})
@login_required
def health_json(request): return JsonResponse(HealthReadiness.summary())
@login_required
def readiness_json(request): return JsonResponse({"ready":HealthReadiness.summary()["status"]=="ready","report":FinalizationReport.build()})
