from django.urls import path
from . import views
app_name="security"
urlpatterns=[path("",views.dashboard,name="dashboard"),path("events/",views.event_list,name="events"),path("audit/",views.audit_list,name="audit"),path("policies/new/",views.policy_create,name="policy_create"),path("incidents/<uuid:pk>/",views.incident_detail,name="incident_detail"),path("sessions/",views.session_list,name="sessions"),path("permissions/",views.permissions,name="permissions")]

from .api_views import SecuritySummaryView,SecurityEventFeedView,AuditFeedView,IncidentFeedView,AlertFeedView,MySessionsView
urlpatterns += [path("feed/summary/",SecuritySummaryView.as_view(),name="api_summary"),path("feed/events/",SecurityEventFeedView.as_view(),name="api_events"),path("feed/audit/",AuditFeedView.as_view(),name="api_audit"),path("feed/incidents/",IncidentFeedView.as_view(),name="api_incidents"),path("feed/alerts/",AlertFeedView.as_view(),name="api_alerts"),path("feed/sessions/",MySessionsView.as_view(),name="api_sessions")]
