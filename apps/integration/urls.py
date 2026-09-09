from django.urls import path
from . import views
app_name="integration"
urlpatterns=[
 path("",views.dashboard,name="dashboard"), path("connections/new/",views.connection_create,name="connection_create"),
 path("jobs/new/",views.job_create,name="job_create"), path("releases/",views.releases,name="releases"), path("releases/new/",views.release_create,name="release_create"),
 path("releases/<uuid:pk>/evaluate/",views.release_evaluate,name="release_evaluate"), path("dead-letters/",views.dead_letters,name="dead_letters"),
 path("health.json",views.health_json,name="health_json"), path("readiness.json",views.readiness_json,name="readiness_json"),
]
