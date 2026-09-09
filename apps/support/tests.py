from django.test import TestCase
from django.utils import timezone
from apps.organizations.models import Organization
from apps.accounts.models import User
from .models import *
from .services import TicketService,SupportReportingService
class SupportPhaseTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='Support Test Org',slug='support-test-org')
        self.user=User.objects.create_user(email='agent@example.com',password='StrongPass123!')
        self.cat=SupportCategory.objects.create(organization=self.org,name='Technical',code='TECH')
    def test_ticket_number_and_creation(self):
        ticket=TicketService.create_ticket(organization=self.org,user=self.user,subject='Login issue',description='Cannot sign in',category=self.cat)
        self.assertTrue(ticket.number.startswith('TKT-')); self.assertEqual(ticket.status,TicketStatus.OPEN)
    def test_status_history(self):
        ticket=TicketService.create_ticket(organization=self.org,user=self.user,subject='Printer',description='Printer offline')
        TicketService.change_status(ticket,TicketStatus.IN_PROGRESS,self.user,'Agent started investigation')
        self.assertEqual(ticket.status,TicketStatus.IN_PROGRESS); self.assertEqual(ticket.status_history.count(),2)
    def test_assignment_history(self):
        team=SupportTeam.objects.create(organization=self.org,name='Tier 1',code='T1')
        ticket=TicketService.create_ticket(organization=self.org,user=self.user,subject='VPN',description='VPN request')
        TicketService.assign(ticket,self.user,team,self.user,'Initial assignment')
        self.assertEqual(ticket.team,team); self.assertEqual(ticket.assignment_history.count(),1)
    def test_message_records_first_response(self):
        requester=User.objects.create_user(email='customer@example.com',password='StrongPass123!')
        ticket=SupportTicket.objects.create(organization=self.org,requester=requester,created_by=requester,subject='Help',description='Need help')
        TicketService.add_message(ticket,self.user,'We are investigating')
        ticket.refresh_from_db(); self.assertIsNotNone(ticket.first_response_at)
    def test_dashboard_counts(self):
        TicketService.create_ticket(organization=self.org,user=self.user,subject='A',description='A')
        TicketService.create_ticket(organization=self.org,user=self.user,subject='B',description='B',priority=TicketPriority.URGENT)
        data=SupportReportingService.dashboard(self.org)
        self.assertEqual(data['total'],2); self.assertEqual(data['urgent'],1)
    def test_satisfaction_validation(self):
        ticket=SupportTicket.objects.create(organization=self.org,created_by=self.user,subject='A',description='A')
        rating=TicketSatisfaction(ticket=ticket,rating=7)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError): rating.full_clean()
