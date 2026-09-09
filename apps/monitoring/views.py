from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import ComponentForm, HealthCheckForm, AlertRuleForm, SLOForm, MaintenanceWindowForm
from .models import ServiceComponent, HealthCheck, MonitoringAlert, Incident, SLODefinition, MaintenanceWindow
from .services import MonitoringDashboardService, IncidentService, AlertService, MaintenanceService, MonitoringAuditService
from .selectors import active_components, open_alerts, active_incidents
from .serializers import component_dict, alert_dict, incident_dict


def _org(request):
    user=request.user
    relation=getattr(user,"organizations",None)
    return relation.first() if relation is not None else None

@login_required
def dashboard(request):
    org=_org(request)
    context={"summary":MonitoringDashboardService.summary(org) if org else {},
             "components":active_components(org)[:20] if org else [],
             "alerts":open_alerts(org)[:20] if org else [],
             "incidents":active_incidents(org)[:20] if org else []}
    return render(request,"monitoring/dashboard.html",context)

@login_required
def component_create(request):
    form=ComponentForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        obj=form.save(); MonitoringAuditService.record(obj.organization,"CREATE","ServiceComponent",obj.id,request.user); messages.success(request,"Component created."); return redirect("monitoring:dashboard")
    return render(request,"monitoring/form.html",{"form":form,"title":"Register service component"})

@login_required
def healthcheck_create(request):
    form=HealthCheckForm(request.POST or None)
    if request.method=="POST" and form.is_valid(): form.save(); messages.success(request,"Health check created."); return redirect("monitoring:dashboard")
    return render(request,"monitoring/form.html",{"form":form,"title":"Create health check"})

@login_required
def alerts(request):
    org=_org(request); return render(request,"monitoring/alerts.html",{"alerts":open_alerts(org) if org else []})

@login_required
def acknowledge_alert(request, pk):
    alert=get_object_or_404(MonitoringAlert,pk=pk); alert.status="ACK"; alert.acknowledged_by=request.user; alert.save(update_fields=["status","acknowledged_by"]); return redirect("monitoring:alerts")

@login_required
def resolve_alert(request, pk):
    alert=get_object_or_404(MonitoringAlert,pk=pk); alert.status="RESOLVED"; alert.resolved_at=timezone.now(); alert.save(update_fields=["status","resolved_at"]); return redirect("monitoring:alerts")

@login_required
def incidents(request):
    org=_org(request); return render(request,"monitoring/incidents.html",{"incidents":active_incidents(org) if org else []})

@login_required
def incident_transition(request, pk, status):
    incident=get_object_or_404(Incident,pk=pk); IncidentService.transition(incident,status,request.user); return redirect("monitoring:incidents")

@login_required
def slo_list(request):
    org=_org(request); return render(request,"monitoring/slo_list.html",{"slos":SLODefinition.objects.filter(organization=org) if org else []})

@login_required
def maintenance_create(request):
    form=MaintenanceWindowForm(request.POST or None)
    if request.method=="POST" and form.is_valid(): form.save(); messages.success(request,"Maintenance window created."); return redirect("monitoring:dashboard")
    return render(request,"monitoring/form.html",{"form":form,"title":"Schedule maintenance"})

@login_required
def maintenance_activate(request, pk):
    window=get_object_or_404(MaintenanceWindow,pk=pk); MaintenanceService.activate(window); return redirect("monitoring:dashboard")

@login_required
def health_json(request):
    org=_org(request); return render(request,"monitoring/json.html",{"payload":[component_dict(x) for x in active_components(org)] if org else []})
