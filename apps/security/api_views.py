"""Read-oriented security endpoints for operational dashboards."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import SecurityEvent,AuditEntry,SecurityIncident,SecurityAlert,UserSession
from .serializers import SecurityEventSerializer,AuditEntrySerializer,SecurityIncidentSerializer,SecurityAlertSerializer,UserSessionSerializer
from .reporting import SecurityReportBuilder

class SecuritySummaryView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        org=getattr(request,"organization",None); report=SecurityReportBuilder(org).executive_report() if org else {}
        return Response(report)
class SecurityEventFeedView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        qs=SecurityEvent.objects.filter(organization=getattr(request,"organization",None)).order_by("-occurred_at")[:100]
        return Response(SecurityEventSerializer(qs,many=True).data)
class AuditFeedView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        qs=AuditEntry.objects.filter(organization=getattr(request,"organization",None)).order_by("-created_at")[:100]
        return Response(AuditEntrySerializer(qs,many=True).data)
class IncidentFeedView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        qs=SecurityIncident.objects.filter(organization=getattr(request,"organization",None)).order_by("-created_at")[:100]
        return Response(SecurityIncidentSerializer(qs,many=True).data)
class AlertFeedView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        qs=SecurityAlert.objects.filter(organization=getattr(request,"organization",None)).order_by("-created_at")[:100]
        return Response(SecurityAlertSerializer(qs,many=True).data)
class MySessionsView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request): return Response(UserSessionSerializer(UserSession.objects.filter(user=request.user),many=True).data)
