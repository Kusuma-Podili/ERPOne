from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import *
from .models import *
from .policies import permission_matrix
from .services import AuditService, IncidentService, PolicyEngine, RiskAssessmentService, SessionSecurityService

@login_required
def dashboard(request):
    org=getattr(request,"organization",None) or request.user.organization_memberships.select_related("organization").first().organization if request.user.organization_memberships.exists() else None
    context={"organization":org,"events":SecurityEvent.objects.filter(organization=org)[:12] if org else [],"event_counts":SecurityEvent.objects.filter(organization=org).values("severity").annotate(total=Count("id")) if org else [],"open_incidents":SecurityIncident.objects.filter(organization=org).exclude(status__in=["RESOLVED","CLOSED"]).count() if org else 0,"open_alerts":SecurityAlert.objects.filter(organization=org,status="OPEN").count() if org else 0,"audit_count":AuditEntry.objects.filter(organization=org).count() if org else 0,"compliance_score":0}
    if org:
        from .services import ComplianceService
        frameworks=ComplianceControl.objects.filter(organization=org).values_list("framework",flat=True).distinct()
        scores=[ComplianceService.framework_score(org,f) for f in frameworks]; context["compliance_score"]=round(sum(scores)/len(scores),2) if scores else 0
    return render(request,"security/dashboard.html",context)

@login_required
def event_list(request):
    qs=SecurityEvent.objects.filter(organization=getattr(request,"organization",None)).select_related("user")
    severity=request.GET.get("severity"); event_type=request.GET.get("event_type")
    if severity: qs=qs.filter(severity=severity)
    if event_type: qs=qs.filter(event_type__icontains=event_type)
    return render(request,"security/event_list.html",{"events":qs[:300],"severity":severity,"event_type":event_type})

@login_required
def audit_list(request):
    qs=AuditEntry.objects.filter(organization=getattr(request,"organization",None)).select_related("actor")
    action=request.GET.get("action"); model=request.GET.get("model")
    if action: qs=qs.filter(action=action)
    if model: qs=qs.filter(model_label__icontains=model)
    return render(request,"security/audit_list.html",{"entries":qs[:300],"action":action,"model":model})

@login_required
def policy_create(request):
    form=SecurityPolicyForm(request.POST or None)
    if form.is_valid():
        policy=form.save(commit=False); policy.created_by=request.user; policy.save(); PolicyEngine.create_version(policy,request.user,"Initial policy"); AuditService.record(actor=request.user,organization=policy.organization,action="CREATE",instance=policy,after={"name":policy.name},request=request); messages.success(request,"Security policy created."); return redirect("security:dashboard")
    return render(request,"security/form.html",{"form":form,"title":"Create Security Policy"})

@login_required
def incident_detail(request,pk):
    incident=get_object_or_404(SecurityIncident,pk=pk,organization=getattr(request,"organization",None));
    if request.method=="POST":
        status=request.POST.get("status",incident.status); IncidentService.transition(incident,status,request.user,request.POST.get("message","")); messages.success(request,"Incident updated."); return redirect("security:incident_detail",pk=pk)
    return render(request,"security/incident_detail.html",{"incident":incident,"timeline":incident.timeline.select_related("actor")})

@login_required
def session_list(request):
    sessions=UserSession.objects.filter(user=request.user).order_by("-last_seen_at")
    if request.method=="POST":
        key=request.POST.get("session_key"); SessionSecurityService.revoke(key,"User revoked session"); messages.success(request,"Session revoked."); return redirect("security:sessions")
    return render(request,"security/sessions.html",{"sessions":sessions})

@login_required
def permissions(request):
    codes=["crm.read","sales.read","finance.read","hr.read","payroll.read","projects.read","support.read","analytics.read","documents.read","notifications.read","security.read","security.audit"]
    return render(request,"security/permissions.html",{"matrix":permission_matrix(request.user,codes)})
