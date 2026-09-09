from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .forms import *
from .models import *
from .services import DomainAnalytics, DashboardService, ReportService, MetricService

def _org(user): return getattr(user,'organization',None) or getattr(user,'current_organization',None)
@login_required
def dashboard(request):
    org=_org(request.user); dashboards=Dashboard.objects.filter(organization=org) if org else Dashboard.objects.none(); metrics=MetricDefinition.objects.filter(organization=org,is_active=True) if org else MetricDefinition.objects.none(); kpis=KPI.objects.filter(organization=org,is_active=True).select_related('metric') if org else KPI.objects.none()
    context={'dashboards':dashboards,'metrics':metrics,'kpis':kpis,'summary':DomainAnalytics.organization(org) if org else {}}
    return render(request,'analytics/dashboard.html',context)
@login_required
def dashboard_detail(request, slug):
    org=_org(request.user); item=get_object_or_404(Dashboard,organization=org,slug=slug); return render(request,'analytics/dashboard_detail.html',{'dashboard':item,'summary':DashboardService.summary(item)})
@login_required
def metric_list(request):
    org=_org(request.user); return render(request,'analytics/metrics.html',{'metrics':MetricDefinition.objects.filter(organization=org)})
@login_required
def metric_create(request):
    org=_org(request.user); form=MetricDefinitionForm(request.POST or None)
    if request.method=='POST' and form.is_valid(): obj=form.save(commit=False); obj.organization=org; obj.created_by=request.user; obj.save(); AnalyticsAuditEvent.objects.create(organization=org,actor=request.user,action='metric_created',entity_type='metric',entity_id=str(obj.pk)); return redirect('analytics:metrics')
    return render(request,'analytics/form.html',{'form':form,'title':'Create Metric'})
@login_required
def report_list(request):
    org=_org(request.user); return render(request,'analytics/reports.html',{'reports':Report.objects.filter(organization=org).annotate(run_count=Count('runs'))})
@login_required
def report_create(request):
    org=_org(request.user); form=ReportForm(request.POST or None)
    if request.method=='POST' and form.is_valid(): obj=form.save(commit=False); obj.organization=org; obj.owner=request.user; obj.save(); return redirect('analytics:reports')
    return render(request,'analytics/form.html',{'form':form,'title':'Create Report'})
@login_required
def report_run(request, pk):
    org=_org(request.user); report=get_object_or_404(Report,pk=pk,organization=org); run=ReportService.run(report,request.user); return JsonResponse({'run_id':str(run.pk),'status':run.status,'row_count':run.row_count,'duration_ms':run.duration_ms,'result':run.result_snapshot})
@login_required
def report_export(request, pk):
    org=_org(request.user); report=get_object_or_404(Report,pk=pk,organization=org); run=ReportService.run(report,request.user); response=HttpResponse('Report,Status,Rows,Duration\n%s,%s,%s,%s\n'%(report.name,run.status,run.row_count,run.duration_ms),content_type='text/csv'); response['Content-Disposition']=f'attachment; filename="{report.code}.csv"'; return response
@login_required
def kpi_detail(request, pk):
    org=_org(request.user); kpi=get_object_or_404(KPI,pk=pk,organization=org); history=MetricService.history(kpi.metric); return render(request,'analytics/kpi_detail.html',{'kpi':kpi,'history':history})
@login_required
def domain_data(request, source):
    org=_org(request.user); funcs={'organization':DomainAnalytics.organization,'sales':DomainAnalytics.sales,'inventory':DomainAnalytics.inventory,'support':DomainAnalytics.support}; fn=funcs.get(source); return JsonResponse(fn(org) if fn and org else {})
