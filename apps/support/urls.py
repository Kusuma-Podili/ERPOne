from django.urls import path
from . import views
app_name='support'
urlpatterns=[
 path('',views.SupportDashboardView.as_view(),name='dashboard'), path('tickets/',views.TicketListView.as_view(),name='tickets'), path('tickets/create/',views.TicketCreateView.as_view(),name='create'), path('tickets/<uuid:pk>/',views.TicketDetailView.as_view(),name='detail'), path('tickets/<uuid:pk>/message/',views.TicketMessageView.as_view(),name='message'), path('tickets/<uuid:pk>/status/',views.TicketStatusView.as_view(),name='status'), path('tickets/<uuid:pk>/assign/',views.TicketAssignmentView.as_view(),name='assign'), path('tickets/<uuid:pk>/satisfaction/',views.SatisfactionView.as_view(),name='satisfaction'), path('knowledge/',views.KnowledgeListView.as_view(),name='knowledge'), path('knowledge/<uuid:pk>/',views.KnowledgeDetailView.as_view(),name='knowledge_detail'), path('knowledge/<uuid:pk>/feedback/',views.KnowledgeFeedbackView.as_view(),name='knowledge_feedback'),
]
