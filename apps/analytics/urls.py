from django.urls import path
from . import views
app_name='analytics'
urlpatterns=[path('',views.dashboard,name='dashboard'),path('dashboards/<slug:slug>/',views.dashboard_detail,name='dashboard_detail'),path('metrics/',views.metric_list,name='metrics'),path('metrics/new/',views.metric_create,name='metric_create'),path('reports/',views.report_list,name='reports'),path('reports/new/',views.report_create,name='report_create'),path('reports/<uuid:pk>/run/',views.report_run,name='report_run'),path('reports/<uuid:pk>/export/',views.report_export,name='report_export'),path('kpis/<uuid:pk>/',views.kpi_detail,name='kpi_detail'),path('data/<str:source>/',views.domain_data,name='domain_data')]
