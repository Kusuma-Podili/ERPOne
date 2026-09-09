"""
EnterpriseOne API URL Configuration.
Root router for RESTful APIs across all modular applications.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path("v1/", include(router.urls)),
]
