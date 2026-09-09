from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import CreateView, DetailView, ListView
from .forms import MLModelForm
from .models import MLModel, ModelVersion, PredictionRequest, ModelDriftEvent
from .services import PredictionService, ModelMonitoringService, ForecastingService

class ModelListView(LoginRequiredMixin,ListView):
    model=MLModel; template_name='ai_engine/model_list.html'; context_object_name='models'; paginate_by=25
    def get_queryset(self): return MLModel.objects.filter(organization__in=self.request.user.organizations.all()).order_by('name')
class ModelCreateView(LoginRequiredMixin,CreateView):
    model=MLModel; form_class=MLModelForm; template_name='ai_engine/model_form.html'; success_url='/ai/models/'
    def form_valid(self,form):
        form.instance.organization=self.request.user.organizations.first(); form.instance.owner=self.request.user; return super().form_valid(form)
class ModelDetailView(LoginRequiredMixin,DetailView):
    model=MLModel; template_name='ai_engine/model_detail.html'; context_object_name='model'
    def get_context_data(self,**kwargs):
        ctx=super().get_context_data(**kwargs); ctx['versions']=self.object.versions.all()[:10]; ctx['latency']=ModelMonitoringService.latency(self.object); ctx['accuracy']=ModelMonitoringService.accuracy_from_feedback(self.object); return ctx

def prediction_view(request,pk):
    model=get_object_or_404(MLModel,pk=pk); features={k:v for k,v in request.GET.items() if k!='csrfmiddlewaretoken'}
    try: prediction=PredictionService.predict(model,features,request.user); return JsonResponse({'prediction':prediction.prediction,'latency_ms':prediction.latency_ms,'version':prediction.version.version})
    except ValueError as exc:return JsonResponse({'error':str(exc)},status=400)

def forecast_view(request):
    values=[float(x) for x in request.GET.getlist('value')]; periods=min(24,max(1,int(request.GET.get('periods',6)))); return JsonResponse({'forecast':ForecastingService.moving_average_forecast(values,periods)})

def model_health_view(request,pk):
    model=get_object_or_404(MLModel,pk=pk); return JsonResponse({'model':model.name,'status':model.status,'latency':ModelMonitoringService.latency(model),'accuracy':ModelMonitoringService.accuracy_from_feedback(model),'versions':model.versions.count(),'predictions':model.prediction_requests.count(),'drift_events':model.drift_events.filter(is_resolved=False).count()})
