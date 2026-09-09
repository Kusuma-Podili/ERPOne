from django.urls import path
from .views import ModelListView, ModelCreateView, ModelDetailView, prediction_view, forecast_view, model_health_view
app_name='ai_engine'
urlpatterns=[path('',ModelListView.as_view(),name='list'),path('models/',ModelListView.as_view(),name='models'),path('models/new/',ModelCreateView.as_view(),name='create'),path('models/<uuid:pk>/',ModelDetailView.as_view(),name='detail'),path('models/<uuid:pk>/predict/',prediction_view,name='predict'),path('models/<uuid:pk>/health/',model_health_view,name='health'),path('forecast/',forecast_view,name='forecast')]
