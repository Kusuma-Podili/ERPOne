"""Domain-specific analytics adapters for EnterpriseOne modules."""
from decimal import Decimal
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
from .services import AnalyticsEngine

class CRMAnalytics:
    @staticmethod
    def pipeline(organization):
        from apps.crm.models import Opportunity
        qs=Opportunity.objects.filter(organization=organization)
        return {'opportunities':qs.count(),'value':qs.aggregate(v=Sum('amount'))['v'] or Decimal('0')}
    @staticmethod
    def accounts_by_type(organization):
        from apps.crm.models import Account
        return list(Account.objects.filter(organization=organization).values('account_type').annotate(total=Count('id')).order_by('-total'))
    @staticmethod
    def recent_accounts(organization, limit=10):
        from apps.crm.models import Account
        return list(Account.objects.filter(organization=organization).order_by('-created_at').values('id','name','created_at')[:limit])

class SalesAnalytics:
    @staticmethod
    def order_summary(organization):
        from apps.sales.models import SalesOrder
        qs=SalesOrder.objects.filter(organization=organization)
        result=qs.aggregate(count=Count('id'),total=Sum('total_amount'),average=Avg('total_amount'))
        return {'count':result['count'] or 0,'total':result['total'] or Decimal('0'),'average':result['average'] or Decimal('0')}
    @staticmethod
    def order_status_breakdown(organization):
        from apps.sales.models import SalesOrder
        return list(SalesOrder.objects.filter(organization=organization).values('status').annotate(total=Count('id')).order_by('-total'))

class ProcurementAnalytics:
    @staticmethod
    def purchase_summary(organization):
        try:
            from apps.procurement.models import PurchaseOrder
            qs=PurchaseOrder.objects.filter(organization=organization)
            result=qs.aggregate(count=Count('id'),total=Sum('total_amount'))
            return {'count':result['count'] or 0,'total':result['total'] or Decimal('0')}
        except (ImportError,AttributeError): return {'count':0,'total':Decimal('0')}

class FinanceAnalytics:
    @staticmethod
    def journal_summary(organization):
        try:
            from apps.finance.models import JournalEntry
            qs=JournalEntry.objects.filter(organization=organization)
            return {'entries':qs.count(),'posted':qs.filter(status='posted').count()}
        except (ImportError,AttributeError): return {'entries':0,'posted':0}

class HRAnalytics:
    @staticmethod
    def workforce(organization):
        from apps.hr.models import Employee
        qs=Employee.objects.filter(organization=organization)
        return {'employees':qs.count(),'active':qs.filter(is_active=True).count() if hasattr(Employee,'is_active') else qs.count()}

class PayrollAnalytics:
    @staticmethod
    def payroll_summary(organization):
        try:
            from apps.payroll.models import PayrollRun
            qs=PayrollRun.objects.filter(organization=organization)
            return {'runs':qs.count()}
        except (ImportError,AttributeError): return {'runs':0}

class ProjectAnalytics:
    @staticmethod
    def delivery(organization):
        from apps.projects.models import Project, ProjectStatus
        qs=Project.objects.filter(organization=organization)
        total=qs.count(); completed=qs.filter(status=ProjectStatus.COMPLETED).count()
        return {'projects':total,'completed':completed,'completion_rate':AnalyticsEngine.percentage(completed,total)}
    @staticmethod
    def overdue_tasks(organization):
        from apps.projects.models import ProjectTask, TaskStatus
        return ProjectTask.objects.filter(project__organization=organization,due_date__lt=timezone.now().date()).exclude(status__in=[TaskStatus.DONE,TaskStatus.CANCELLED]).count()

class SupportAnalytics:
    @staticmethod
    def ticket_metrics(organization):
        from apps.support.models import SupportTicket, TicketStatus
        qs=SupportTicket.objects.filter(organization=organization); total=qs.count(); resolved=qs.filter(status__in=[TicketStatus.RESOLVED,TicketStatus.CLOSED]).count()
        avg_response=qs.exclude(first_response_at__isnull=True).aggregate(v=Avg('first_response_at'))['v']
        return {'total':total,'resolved':resolved,'open':total-resolved,'resolution_rate':AnalyticsEngine.percentage(resolved,total),'first_response_reference':avg_response}
    @staticmethod
    def priority_breakdown(organization):
        from apps.support.models import SupportTicket
        return list(SupportTicket.objects.filter(organization=organization).values('priority').annotate(total=Count('id')).order_by('-total'))

class ExecutiveAnalytics:
    @staticmethod
    def snapshot(organization):
        return {'generated_at':timezone.now().isoformat(),'crm':CRMAnalytics.pipeline(organization),'sales':SalesAnalytics.order_summary(organization),'procurement':ProcurementAnalytics.purchase_summary(organization),'finance':FinanceAnalytics.journal_summary(organization),'hr':HRAnalytics.workforce(organization),'payroll':PayrollAnalytics.payroll_summary(organization),'projects':ProjectAnalytics.delivery(organization),'support':SupportAnalytics.ticket_metrics(organization)}
