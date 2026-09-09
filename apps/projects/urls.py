from django.urls import path
from . import views
app_name='projects'
urlpatterns=[
 path('',views.ProjectDashboardView.as_view(),name='dashboard'),
 path('list/',views.ProjectListView.as_view(),name='list'),
 path('create/',views.ProjectCreateView.as_view(),name='create'),
 path('<uuid:pk>/',views.ProjectDetailView.as_view(),name='detail'),
 path('<uuid:pk>/edit/',views.ProjectUpdateView.as_view(),name='edit'),
 path('<uuid:project_id>/tasks/',views.TaskListView.as_view(),name='tasks'),
 path('<uuid:project_id>/tasks/create/',views.TaskCreateView.as_view(),name='task_create'),
 path('<uuid:pk>/task/',views.TaskDetailView.as_view(),name='task_detail'),
 path('<uuid:pk>/task/edit/',views.TaskUpdateView.as_view(),name='task_edit'),
 path('<uuid:project_id>/milestones/create/',views.MilestoneCreateView.as_view(),name='milestone_create'),
 path('<uuid:project_id>/time/create/',views.TimeEntryCreateView.as_view(),name='time_create'),
 path('<uuid:project_id>/expenses/create/',views.ExpenseCreateView.as_view(),name='expense_create'),
]
