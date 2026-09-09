from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.organizations.models import Organization
from .models import *
from .services import AnalyticsEngine, MetricService, DashboardService, ReportService
User=get_user_model()
class AnalyticsEngineTests(TestCase):
    def test_percentage_and_trend(self):
        self.assertEqual(AnalyticsEngine.percentage(25,100),Decimal('25.00'))
        self.assertEqual(AnalyticsEngine.trend([10,12,15])['direction'],'up')
        self.assertEqual(len(AnalyticsEngine.moving_average([1,2,3,4],2)),4)
class AnalyticsModelTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='Analytics Org',code='ANL01')
        self.user=User.objects.create_user(email='analyst@example.com',password='StrongPass123!')
        self.metric=MetricDefinition.objects.create(organization=self.org,name='Orders',code='orders',source=DataSource.SALES,metric_type=MetricType.COUNT,expression='count(orders)',created_by=self.user)
    def test_snapshot_and_kpi(self):
        snap=MetricService.record_snapshot(self.metric,42,timezone.now()); self.assertEqual(snap.value,Decimal('42'))
        kpi=KPI.objects.create(organization=self.org,metric=self.metric,name='Orders KPI',target=50,warning_threshold=30,critical_threshold=10)
        self.assertEqual(MetricService.evaluate_kpi(kpi,42)['status'],'on_target')
    def test_dashboard_summary(self):
        d=Dashboard.objects.create(organization=self.org,name='Executive',slug='executive',owner=self.user)
        DashboardWidget.objects.create(dashboard=d,title='Orders',widget_type=WidgetType.KPI,metric=self.metric)
        self.assertEqual(len(DashboardService.summary(d)['widgets']),1)
    def test_report_run(self):
        r=Report.objects.create(organization=self.org,name='Sales Report',code='sales-report',source=DataSource.SALES,columns=['date','amount'],owner=self.user)
        run=ReportService.run(r,self.user); self.assertEqual(run.status,'completed')
