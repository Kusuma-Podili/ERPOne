from django.utils import timezone
from datetime import timedelta
from .models import ModelDeployment, MLModel
# Lightweight task functions intentionally framework-agnostic; a queue can call them later.
def retire_stale_deployments(hours=24):
    cutoff=timezone.now()-timedelta(hours=hours)
    return ModelDeployment.objects.filter(active=True,deployed_at__lt=cutoff).update(active=False,retired_at=timezone.now())

def model_inventory(organization):
    return list(MLModel.objects.filter(organization=organization).values('id','name','status','problem_type','updated_at'))
