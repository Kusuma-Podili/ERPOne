from django.urls import path
from . import views
app_name='notifications'
urlpatterns=[path('',views.inbox,name='inbox'),path('list/',views.inbox,name='list'),path('read/<uuid:pk>/',views.mark_read,name='mark_read'),path('read-all/',views.mark_all_read,name='mark_all_read'),path('preferences/',views.preferences,name='preferences'),path('templates/',views.templates,name='templates'),path('templates/new/',views.template_create,name='template_create'),path('retry/',views.retry_failed,name='retry_failed')]
