from django.urls import path
from . import views
app_name='documents'
urlpatterns=[path('',views.dashboard,name='dashboard'),path('list/',views.document_list,name='list'),path('new/',views.document_create,name='create'),path('<uuid:pk>/',views.detail,name='detail'),path('<uuid:pk>/upload/',views.upload_version,name='upload_version'),path('<uuid:pk>/download/',views.download,name='download'),path('<uuid:pk>/download/<int:version>/',views.download,name='download_version'),path('<uuid:pk>/approve/',views.approve,name='approve'),path('<uuid:pk>/archive/',views.archive,name='archive')]
