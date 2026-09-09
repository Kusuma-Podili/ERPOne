from django.contrib import messages
from django.shortcuts import get_object_or_404,redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView,ListView,CreateView,DetailView
from apps.organizations.views import OrganizationAccessMixin
from .models import PayrollComponent,SalaryStructure,PayrollPeriod,Payslip
from .forms import PayrollComponentForm,SalaryStructureForm,PayrollPeriodForm
from .services import PayrollRunService
class Dashboard(OrganizationAccessMixin,TemplateView):
 template_name='payroll/dashboard.html'
 def get_context_data(self,**k):
  c=super().get_context_data(**k); p=PayrollPeriod.objects.filter(organization=self.request.organization).first(); c.update(current_period=p,totals=PayrollRunService.totals(p) if p else None); return c
class Components(OrganizationAccessMixin,ListView):
 model=PayrollComponent; template_name='payroll/simple_list.html'; context_object_name='items'
 def get_queryset(self): return PayrollComponent.objects.filter(organization=self.request.organization)
class ComponentCreate(OrganizationAccessMixin,CreateView):
 form_class=PayrollComponentForm; template_name='payroll/form.html'; success_url=reverse_lazy('payroll:components')
 def get_form_kwargs(self): k=super().get_form_kwargs(); k['organization']=self.request.organization; return k
class Structures(Components): model=SalaryStructure
class StructureCreate(ComponentCreate): form_class=SalaryStructureForm; success_url=reverse_lazy('payroll:structures')
class Periods(Components): model=PayrollPeriod; template_name='payroll/period_list.html'; context_object_name='periods'
class PeriodCreate(ComponentCreate): form_class=PayrollPeriodForm; success_url=reverse_lazy('payroll:periods')
class PeriodDetail(OrganizationAccessMixin,DetailView):
 model=PayrollPeriod; template_name='payroll/period_detail.html'
 def get_queryset(self): return PayrollPeriod.objects.filter(organization=self.request.organization)
class Process(OrganizationAccessMixin,TemplateView):
 def post(self,request,pk):
  p=get_object_or_404(PayrollPeriod,pk=pk,organization=request.organization)
  try: n=PayrollRunService.process(p,request.user); messages.success(request,f'{n} payslips generated.')
  except Exception as e: messages.error(request,str(e))
  return redirect('payroll:period_detail',pk=pk)
class Approve(Process):
 def post(self,request,pk):
  p=get_object_or_404(PayrollPeriod,pk=pk,organization=request.organization)
  try: PayrollRunService.approve(p,request.user); messages.success(request,'Payroll approved.')
  except Exception as e: messages.error(request,str(e))
  return redirect('payroll:period_detail',pk=pk)
class Payslips(OrganizationAccessMixin,ListView):
 model=Payslip; template_name='payroll/payslip_list.html'; context_object_name='payslips'
 def get_queryset(self): return Payslip.objects.filter(period__organization=self.request.organization).select_related('employee','period')
