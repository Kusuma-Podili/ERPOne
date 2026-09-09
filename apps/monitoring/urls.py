from django.urls import path
from . import views
app_name="monitoring"
urlpatterns=[
 path("",views.dashboard,name="dashboard"), path("components/new/",views.component_create,name="component_create"),
 path("health-checks/new/",views.healthcheck_create,name="healthcheck_create"), path("alerts/",views.alerts,name="alerts"),
 path("alerts/<uuid:pk>/acknowledge/",views.acknowledge_alert,name="acknowledge_alert"), path("alerts/<uuid:pk>/resolve/",views.resolve_alert,name="resolve_alert"),
 path("incidents/",views.incidents,name="incidents"), path("incidents/<uuid:pk>/<str:status>/",views.incident_transition,name="incident_transition"),
 path("slos/",views.slo_list,name="slo_list"), path("maintenance/new/",views.maintenance_create,name="maintenance_create"),
 path("maintenance/<uuid:pk>/activate/",views.maintenance_activate,name="maintenance_activate"), path("health.json",views.health_json,name="health_json"),
]
