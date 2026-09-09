from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404,redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView,ListView,CreateView,DetailView,UpdateView
from apps.organizations.views import OrganizationAccessMixin
from .models import *
from .forms import *
from .services import LeaveService
class HRDashboardView(OrganizationAccessMixin,TemplateView):
 template_name='hr/dashboard.html'
 def get_context_data(self,**k):
  c=super().get_context_data(**k); o=self.request.organization; c.update(active_count=Employee.objects.filter(organization=o,employment_status='active').count(),on_leave_count=Employee.objects.filter(organization=o,employment_status='on_leave').count(),pending_leave=LeaveRequest.objects.filter(employee__organization=o,status='pending').count(),recent_hires=Employee.objects.filter(organization=o).select_related('department','position').order_by('-hire_date')[:8]); return c
class EmployeeListView(OrganizationAccessMixin,ListView):
 model=Employee; template_name='hr/employee_list.html'; context_object_name='employees'; paginate_by=40
 def get_queryset(self):
  qs=Employee.objects.filter(organization=self.request.organization).select_related('department','position','manager'); q=self.request.GET.get('q','').strip(); return qs.filter(Q(employee_number__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q)|Q(work_email__icontains=q)) if q else qs
class EmployeeCreateView(OrganizationAccessMixin,CreateView):
 form_class=EmployeeForm; template_name='hr/form.html'; success_url=reverse_lazy('hr:employee_list')
 def get_form_kwargs(self): k=super().get_form_kwargs(); k['organization']=self.request.organization; return k
class EmployeeDetailView(OrganizationAccessMixin,DetailView):
 model=Employee; template_name='hr/employee_detail.html'
 def get_queryset(self): return Employee.objects.filter(organization=self.request.organization).select_related('department','position','manager')
class EmployeeUpdateView(EmployeeCreateView,UpdateView):
 def get_queryset(self): return Employee.objects.filter(organization=self.request.organization)
class PositionListView(OrganizationAccessMixin,ListView):
 model=JobPosition; template_name='hr/simple_list.html'; context_object_name='items'
 def get_queryset(self): return JobPosition.objects.filter(organization=self.request.organization)
class PositionCreateView(EmployeeCreateView): form_class=JobPositionForm; success_url=reverse_lazy('hr:position_list')
class ShiftListView(PositionListView): model=Shift
class ShiftCreateView(EmployeeCreateView): form_class=ShiftForm; success_url=reverse_lazy('hr:shift_list')
class LeavePolicyListView(PositionListView): model=LeavePolicy
class LeavePolicyCreateView(EmployeeCreateView): form_class=LeavePolicyForm; success_url=reverse_lazy('hr:leave_policy_list')
class LeaveListView(OrganizationAccessMixin,ListView):
 model=LeaveRequest; template_name='hr/leave_list.html'; context_object_name='requests'
 def get_queryset(self): return LeaveRequest.objects.filter(employee__organization=self.request.organization).select_related('employee','policy','approver')
class LeaveCreateView(OrganizationAccessMixin,CreateView):
 form_class=LeaveRequestForm; template_name='hr/form.html'; success_url=reverse_lazy('hr:leave_list')
 def get_form(self,*a,**k):
  f=super().get_form(*a,**k); f.fields['policy'].queryset=LeavePolicy.objects.filter(organization=self.request.organization,is_active=True); return f
 def form_valid(self,form):
  employee=get_object_or_404(Employee,pk=self.request.POST.get('employee'),organization=self.request.organization); obj=form.save(False); obj.employee=employee
  try: LeaveService.submit(obj,self.request.user)
  except Exception as e: form.add_error(None,str(e)); return self.form_invalid(form)
  messages.success(self.request,'Leave request submitted.'); return redirect(self.success_url)
class AttendanceListView(OrganizationAccessMixin,ListView):
 model=AttendanceRecord; template_name='hr/attendance_list.html'; context_object_name='records'
 def get_queryset(self): return AttendanceRecord.objects.filter(employee__organization=self.request.organization).select_related('employee','shift')
class PerformanceListView(OrganizationAccessMixin,ListView):
 model=PerformanceCycle; template_name='hr/simple_list.html'; context_object_name='items'
 def get_queryset(self): return PerformanceCycle.objects.filter(organization=self.request.organization)
class PerformanceCreateView(EmployeeCreateView): form_class=PerformanceCycleForm; success_url=reverse_lazy('hr:performance_list')
