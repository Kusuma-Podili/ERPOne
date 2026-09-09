from django.db import transaction
from django.db.models import Count,Q,Avg,F,ExpressionWrapper,DurationField
from django.utils import timezone
from .models import *

class TicketService:
    @staticmethod
    @transaction.atomic
    def create_ticket(*,organization,user,subject,description,customer=None,category=None,priority=None,source=TicketSource.PORTAL,ticket_type=TicketType.INCIDENT,tags=None):
        priority=priority or (category.default_priority if category else TicketPriority.NORMAL)
        sla=SlaPolicy.objects.filter(organization=organization,priority=priority,is_active=True).order_by('resolution_minutes').first()
        ticket=SupportTicket.objects.create(organization=organization,created_by=user,requester=user,subject=subject,description=description,customer=customer,category=category,priority=priority,source=source,ticket_type=ticket_type,tags=tags or [],sla_policy=sla)
        TicketStatusHistory.objects.create(ticket=ticket,to_status=ticket.status,changed_by=user,note='Ticket created')
        if sla:
            first,resolution=sla.deadlines(ticket.created_at); ticket.due_at=resolution; ticket.save(update_fields=['due_at','updated_at'])
            TicketSlaEvent.objects.create(ticket=ticket,event_type='resolution_target',status=SlaStatus.ACTIVE,target_at=resolution)
        return ticket
    @staticmethod
    @transaction.atomic
    def change_status(ticket,status,user=None,note=''):
        old=ticket.status
        if old==status:return ticket
        ticket.status=status
        now=timezone.now()
        if status==TicketStatus.RESOLVED: ticket.resolved_at=now
        if status==TicketStatus.CLOSED: ticket.closed_at=now
        if status in (TicketStatus.OPEN,TicketStatus.REOPENED): ticket.resolved_at=None; ticket.closed_at=None
        ticket.save(update_fields=['status','resolved_at','closed_at','updated_at'])
        TicketStatusHistory.objects.create(ticket=ticket,from_status=old,to_status=status,changed_by=user,note=note)
        return ticket
    @staticmethod
    @transaction.atomic
    def assign(ticket,user=None,team=None,changed_by=None,reason=''):
        old_user,old_team=ticket.assignee,ticket.team
        ticket.assignee=user; ticket.team=team; ticket.save(update_fields=['assignee','team','updated_at'])
        TicketAssignmentHistory.objects.create(ticket=ticket,previous_assignee=old_user,new_assignee=user,previous_team=old_team,new_team=team,changed_by=changed_by,reason=reason)
        return ticket
    @staticmethod
    @transaction.atomic
    def add_message(ticket,author,body,is_internal=False,channel=TicketSource.PORTAL):
        msg=TicketMessage.objects.create(ticket=ticket,author=author,body=body,is_internal=is_internal,channel=channel)
        if not is_internal and not ticket.first_response_at and author_id_not_requester(author,ticket):
            ticket.first_response_at=msg.created_at; ticket.save(update_fields=['first_response_at','updated_at'])
            TicketSlaEvent.objects.create(ticket=ticket,event_type='first_response',status=SlaStatus.MET,occurred_at=msg.created_at)
        return msg

def author_id_not_requester(author,ticket): return bool(author and (not ticket.requester_id or author.pk!=ticket.requester_id))

class SupportReportingService:
    @staticmethod
    def dashboard(organization):
        qs=SupportTicket.objects.filter(organization=organization)
        open_q=qs.exclude(status__in=[TicketStatus.RESOLVED,TicketStatus.CLOSED])
        return {'total':qs.count(),'open':open_q.count(),'urgent':qs.filter(priority__in=[TicketPriority.URGENT,TicketPriority.CRITICAL]).exclude(status__in=[TicketStatus.RESOLVED,TicketStatus.CLOSED]).count(),'overdue':sum(1 for t in open_q.only('due_at','status') if t.is_overdue),'resolved':qs.filter(status=TicketStatus.RESOLVED).count(),'closed':qs.filter(status=TicketStatus.CLOSED).count(),'unassigned':qs.filter(assignee__isnull=True).exclude(status__in=[TicketStatus.RESOLVED,TicketStatus.CLOSED]).count(),'avg_rating':qs.filter(satisfaction__isnull=False).aggregate(v=Avg('satisfaction__rating'))['v'] or 0,'by_status':list(qs.values('status').annotate(count=Count('id')).order_by('-count')),'by_priority':list(qs.values('priority').annotate(count=Count('id')).order_by('-count')),'by_category':list(qs.values('category__name').annotate(count=Count('id')).order_by('-count')[:10])}
    @staticmethod
    def agent_workload(organization):
        return list(SupportTicket.objects.filter(organization=organization).exclude(status__in=[TicketStatus.RESOLVED,TicketStatus.CLOSED]).values('assignee_id','assignee__email').annotate(open_count=Count('id')).order_by('-open_count'))
    @staticmethod
    def sla_breaches(organization):
        return SupportTicket.objects.filter(organization=organization,due_at__lt=timezone.now()).exclude(status__in=[TicketStatus.RESOLVED,TicketStatus.CLOSED]).select_related('assignee','team','category')

class KnowledgeBaseService:
    @staticmethod
    def search(organization,query):
        qs=KnowledgeArticle.objects.filter(organization=organization,is_published=True)
        if query:
            qs=qs.filter(Q(title__icontains=query)|Q(summary__icontains=query)|Q(content__icontains=query))
        return qs.order_by('-helpful_count','title')
    @staticmethod
    def record_feedback(article,helpful):
        field='helpful_count' if helpful else 'not_helpful_count'; setattr(article,field,getattr(article,field)+1); article.save(update_fields=[field,'updated_at'])
