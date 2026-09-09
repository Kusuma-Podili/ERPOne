from django.contrib import messages
from django.shortcuts import get_object_or_404,redirect
from django.urls import reverse
from django.views.generic import TemplateView,ListView,CreateView,DetailView,UpdateView,FormView
from django.db.models import Q
from apps.organizations.views import OrganizationAccessMixin
from .models import *
from .forms import *
from .services import TicketService,SupportReportingService,KnowledgeBaseService

class SupportDashboardView(OrganizationAccessMixin,TemplateView):
    template_name='support/dashboard.html'
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); o=self.request.organization; c['dashboard']=SupportReportingService.dashboard(o); c['workload']=SupportReportingService.agent_workload(o); c['breaches']=SupportReportingService.sla_breaches(o)[:10]; c['recent']=SupportTicket.objects.filter(organization=o).select_related('assignee','category','customer')[:10]; return c
class TicketListView(OrganizationAccessMixin,ListView):
    template_name='support/ticket_list.html'; context_object_name='tickets'; paginate_by=25
    def get_queryset(self):
        qs=SupportTicket.objects.filter(organization=self.request.organization).select_related('assignee','team','category','customer'); q=self.request.GET.get('q','').strip(); status=self.request.GET.get('status',''); priority=self.request.GET.get('priority','');
        if q: qs=qs.filter(Q(number__icontains=q)|Q(subject__icontains=q)|Q(description__icontains=q))
        if status: qs=qs.filter(status=status)
        if priority: qs=qs.filter(priority=priority)
        return qs
class TicketCreateView(OrganizationAccessMixin,CreateView):
    form_class=TicketForm; template_name='support/ticket_form.html'
    def get_form(self,*a,**k):
        f=super().get_form(*a,**k); f.fields['category'].queryset=SupportCategory.objects.filter(organization=self.request.organization,is_active=True); from apps.crm.models import Account; f.fields['customer'].queryset=Account.objects.filter(organization=self.request.organization); return f
    def form_valid(self,form):
        t=TicketService.create_ticket(organization=self.request.organization,user=self.request.user,**form.cleaned_data); messages.success(self.request,f'Ticket {t.number} created.'); return redirect('support:detail',pk=t.pk)
class TicketDetailView(OrganizationAccessMixin,DetailView):
    model=SupportTicket; template_name='support/ticket_detail.html'; context_object_name='ticket'
    def get_queryset(self): return SupportTicket.objects.filter(organization=self.request.organization).select_related('customer','category','team','assignee','sla_policy')
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); c['message_form']=TicketMessageForm(); c['assignment_form']=AssignmentForm(organization=self.request.organization); c['history']=self.object.status_history.select_related('changed_by')[:20]; c['messages']=self.object.messages.select_related('author'); return c
class TicketMessageView(OrganizationAccessMixin,FormView):
    form_class=TicketMessageForm
    def post(self,request,*args,**kwargs):
        ticket=get_object_or_404(SupportTicket,pk=kwargs['pk'],organization=request.organization); form=self.form_class(request.POST)
        if form.is_valid(): TicketService.add_message(ticket,request.user,**form.cleaned_data); messages.success(request,'Message added.')
        return redirect('support:detail',pk=ticket.pk)
class TicketStatusView(OrganizationAccessMixin,FormView):
    def post(self,request,*args,**kwargs):
        ticket=get_object_or_404(SupportTicket,pk=kwargs['pk'],organization=request.organization); status=request.POST.get('status',''); note=request.POST.get('note','')
        if status in dict(TicketStatus.choices): TicketService.change_status(ticket,status,request.user,note); messages.success(request,'Ticket status updated.')
        return redirect('support:detail',pk=ticket.pk)
class TicketAssignmentView(OrganizationAccessMixin,FormView):
    def post(self,request,*args,**kwargs):
        ticket=get_object_or_404(SupportTicket,pk=kwargs['pk'],organization=request.organization); form=AssignmentForm(request.POST,organization=request.organization)
        if form.is_valid(): TicketService.assign(ticket,form.cleaned_data['assignee'],form.cleaned_data['team'],request.user,form.cleaned_data['reason']); messages.success(request,'Ticket assignment updated.')
        return redirect('support:detail',pk=ticket.pk)
class SatisfactionView(OrganizationAccessMixin,CreateView):
    form_class=SatisfactionForm; template_name='support/satisfaction_form.html'
    def dispatch(self,request,*args,**kwargs): self.ticket=get_object_or_404(SupportTicket,pk=kwargs['pk'],organization=request.organization); return super().dispatch(request,*args,**kwargs)
    def form_valid(self,form): self.object=form.save(commit=False); self.object.ticket=self.ticket; self.object.submitted_by=self.request.user; self.object.save(); messages.success(self.request,'Thank you for your feedback.'); return redirect('support:detail',pk=self.ticket.pk)
class KnowledgeListView(OrganizationAccessMixin,ListView):
    template_name='support/knowledge_list.html'; context_object_name='articles'; paginate_by=20
    def get_queryset(self): return KnowledgeBaseService.search(self.request.organization,self.request.GET.get('q',''))
class KnowledgeDetailView(OrganizationAccessMixin,DetailView):
    model=KnowledgeArticle; template_name='support/knowledge_detail.html'; context_object_name='article'
    def get_queryset(self): return KnowledgeArticle.objects.filter(organization=self.request.organization,is_published=True)
    def get_object(self,queryset=None):
        obj=super().get_object(queryset); obj.view_count+=1; obj.save(update_fields=['view_count','updated_at']); return obj
class KnowledgeFeedbackView(OrganizationAccessMixin,FormView):
    def post(self,request,*args,**kwargs):
        article=get_object_or_404(KnowledgeArticle,pk=kwargs['pk'],organization=request.organization,is_published=True); KnowledgeBaseService.record_feedback(article,request.POST.get('helpful')=='1'); return redirect('support:knowledge_detail',pk=article.pk)
