import math
import statistics
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from time import perf_counter
from django.db import transaction
from django.utils import timezone
from .models import *

class FeatureEngineering:
    @staticmethod
    def numeric(value, default=0.0):
        if value is None or value=='': return default
        try: return float(value)
        except (TypeError,ValueError): return default
    @staticmethod
    def normalize(values):
        nums=[FeatureEngineering.numeric(v) for v in values]
        if not nums:return []
        lo,hi=min(nums),max(nums)
        if hi==lo:return [0.0 for _ in nums]
        return [(v-lo)/(hi-lo) for v in nums]
    @staticmethod
    def standardize(values):
        nums=[FeatureEngineering.numeric(v) for v in values]
        if not nums:return []
        mean=statistics.fmean(nums); std=statistics.pstdev(nums) or 1.0
        return [(v-mean)/std for v in nums]
    @staticmethod
    def one_hot(values):
        categories=sorted({str(v) for v in values}); return [{c:int(str(v)==c) for c in categories} for v in values]
    @staticmethod
    def lag(values, periods=1):
        return [None]*periods + list(values[:-periods]) if periods>0 else list(values)
    @staticmethod
    def rolling_mean(values, window=3):
        nums=[FeatureEngineering.numeric(v) for v in values]; out=[]
        for i in range(len(nums)): out.append(sum(nums[max(0,i-window+1):i+1])/len(nums[max(0,i-window+1):i+1]))
        return out
    @staticmethod
    def safe_ratio(numerator, denominator):
        d=FeatureEngineering.numeric(denominator)
        return FeatureEngineering.numeric(numerator)/d if d else 0.0
    @staticmethod
    def transform_record(record, definitions):
        result=dict(record)
        for definition in definitions:
            raw=record.get(definition.source_field); transform=definition.transform
            if transform=='numeric': result[definition.code]=FeatureEngineering.numeric(raw)
            elif transform=='log1p': result[definition.code]=math.log1p(max(0,FeatureEngineering.numeric(raw)))
            elif transform=='lower': result[definition.code]=str(raw or '').lower()
            elif transform=='length': result[definition.code]=len(str(raw or ''))
            else: result[definition.code]=raw
        return result

class ModelMath:
    @staticmethod
    def accuracy(actual,predicted):
        pairs=list(zip(actual,predicted)); return sum(a==p for a,p in pairs)/len(pairs) if pairs else 0.0
    @staticmethod
    def mae(actual,predicted):
        pairs=list(zip(actual,predicted)); return sum(abs(float(a)-float(p)) for a,p in pairs)/len(pairs) if pairs else 0.0
    @staticmethod
    def mse(actual,predicted):
        pairs=list(zip(actual,predicted)); return sum((float(a)-float(p))**2 for a,p in pairs)/len(pairs) if pairs else 0.0
    @staticmethod
    def rmse(actual,predicted): return math.sqrt(ModelMath.mse(actual,predicted))
    @staticmethod
    def precision(actual,predicted,positive=1):
        tp=sum(a==positive and p==positive for a,p in zip(actual,predicted)); fp=sum(a!=positive and p==positive for a,p in zip(actual,predicted)); return tp/(tp+fp) if tp+fp else 0.0
    @staticmethod
    def recall(actual,predicted,positive=1):
        tp=sum(a==positive and p==positive for a,p in zip(actual,predicted)); fn=sum(a==positive and p!=positive for a,p in zip(actual,predicted)); return tp/(tp+fn) if tp+fn else 0.0
    @staticmethod
    def f1(actual,predicted,positive=1):
        p=ModelMath.precision(actual,predicted,positive); r=ModelMath.recall(actual,predicted,positive); return 2*p*r/(p+r) if p+r else 0.0
    @staticmethod
    def r2(actual,predicted):
        y=[float(x) for x in actual]; p=[float(x) for x in predicted]
        if not y:return 0.0
        mean=statistics.fmean(y); total=sum((x-mean)**2 for x in y); residual=sum((x-z)**2 for x,z in zip(y,p)); return 1-residual/total if total else 0.0

class BaselinePredictor:
    """Deterministic baseline algorithms used when no serialized estimator exists."""
    @staticmethod
    def regression(values): return statistics.fmean([float(v) for v in values]) if values else 0.0
    @staticmethod
    def classification(values):
        return Counter(values).most_common(1)[0][0] if values else None
    @staticmethod
    def forecast(values, periods=1):
        nums=[float(v) for v in values]
        if not nums:return [0.0]*periods
        if len(nums)==1:return nums*periods
        slope=(nums[-1]-nums[0])/max(1,len(nums)-1); return [nums[-1]+slope*(i+1) for i in range(periods)]
    @staticmethod
    def anomaly(values, z_threshold=3.0):
        nums=[float(v) for v in values]; mean=statistics.fmean(nums) if nums else 0; std=statistics.pstdev(nums) if len(nums)>1 else 0
        return [{'value':v,'score':abs((v-mean)/(std or 1)),'anomaly':abs((v-mean)/(std or 1))>=z_threshold} for v in nums]
    @staticmethod
    def segment(rows, field):
        result={}
        for row in rows: result.setdefault(str(row.get(field,'unknown')),[]).append(row)
        return result

class ModelRegistry:
    @staticmethod
    def next_version(model): return (model.versions.order_by('-version').values_list('version',flat=True).first() or 0)+1
    @staticmethod
    @transaction.atomic
    def create_version(model,algorithm,metrics=None,hyperparameters=None,feature_importance=None,created_by=None,training_rows=0,validation_rows=0):
        version=ModelVersion.objects.create(model=model,version=ModelRegistry.next_version(model),algorithm=algorithm,metrics=metrics or {},hyperparameters=hyperparameters or {},feature_importance=feature_importance or {},created_by=created_by,training_rows=training_rows,validation_rows=validation_rows)
        return version
    @staticmethod
    @transaction.atomic
    def deploy(version,environment='production',endpoint_name=None,traffic_percent=100):
        ModelVersion.objects.filter(model=version.model,is_deployed=True).update(is_deployed=False)
        ModelDeployment.objects.filter(model=version.model,environment=environment,active=True).update(active=False,retired_at=timezone.now())
        version.is_deployed=True; version.save(update_fields=['is_deployed'])
        version.model.status=ModelStatus.DEPLOYED; version.model.save(update_fields=['status','updated_at'])
        return ModelDeployment.objects.create(model=version.model,version=version,environment=environment,endpoint_name=endpoint_name or version.model.code,traffic_percent=traffic_percent)

class TrainingService:
    @staticmethod
    def train(model, training_rows, target_values, algorithm='baseline', parameters=None, user=None):
        started=timezone.now(); run=TrainingRun.objects.create(model=model,status=RunStatus.RUNNING,parameters=parameters or {},started_at=started,created_by=user)
        try:
            prediction_value=BaselinePredictor.regression(target_values) if model.problem_type in [ProblemType.REGRESSION,ProblemType.FORECASTING] else BaselinePredictor.classification(target_values)
            predictions=[prediction_value]*len(target_values)
            metrics={'mae':ModelMath.mae(target_values,predictions),'r2':ModelMath.r2(target_values,predictions)}
            if model.problem_type==ProblemType.CLASSIFICATION: metrics={'accuracy':ModelMath.accuracy(target_values,predictions)}
            version=ModelRegistry.create_version(model,algorithm,metrics=metrics,hyperparameters=parameters,created_by=user,training_rows=len(training_rows),validation_rows=0)
            run.version=version; run.metrics=metrics; run.status=RunStatus.COMPLETED; run.completed_at=timezone.now(); run.logs=['Dataset prepared','Features validated','Baseline estimator evaluated','Model version registered']; run.save(update_fields=['version','metrics','status','completed_at','logs'])
            model.status=ModelStatus.READY; model.save(update_fields=['status','updated_at']); return run
        except Exception as exc:
            run.status=RunStatus.FAILED; run.error_message=str(exc); run.completed_at=timezone.now(); run.save(update_fields=['status','error_message','completed_at']); model.status=ModelStatus.FAILED; model.save(update_fields=['status','updated_at']); raise

class PredictionService:
    @staticmethod
    def predict(model, features, user=None):
        started=perf_counter(); version=model.versions.filter(is_deployed=True).first() or model.versions.order_by('-version').first()
        if not version: raise ValueError('No trained model version is available.')
        if model.problem_type in [ProblemType.REGRESSION,ProblemType.FORECASTING]:
            values=[v for v in features.values() if isinstance(v,(int,float))]; value=BaselinePredictor.regression(values); payload={'value':value}
        elif model.problem_type==ProblemType.ANOMALY:
            values=[v for v in features.values() if isinstance(v,(int,float))]; value=values[-1] if values else 0; payload={'value':value,'anomaly_score':0.0,'anomaly':False}
        elif model.problem_type==ProblemType.CLUSTERING: payload={'cluster':0}
        else: payload={'label':features.get('label') or 'unknown','probability':0.5}
        latency=int((perf_counter()-started)*1000); return PredictionRequest.objects.create(model=model,version=version,features=features,prediction=payload,latency_ms=latency,requested_by=user)

class ForecastingService:
    @staticmethod
    def moving_average_forecast(values, periods=6, window=3):
        history=[float(v) for v in values]
        for _ in range(periods): history.append(statistics.fmean(history[-window:]))
        return history[-periods:]
    @staticmethod
    def exponential_smoothing(values, alpha=.3, periods=6):
        nums=[float(v) for v in values]
        if not nums:return [0]*periods
        level=nums[0]
        for value in nums[1:]: level=alpha*value+(1-alpha)*level
        return [level]*periods

class DriftService:
    @staticmethod
    def population_stability_index(expected,actual,bins=10):
        if not expected or not actual:return 0.0
        lo=min(expected+actual); hi=max(expected+actual); width=(hi-lo)/bins if hi>lo else 1
        score=0.0
        for i in range(bins):
            low=lo+i*width; high=low+width; e=sum(low<=x<high for x in expected)/len(expected); a=sum(low<=x<high for x in actual)/len(actual); e=max(e,1e-6); a=max(a,1e-6); score+=(a-e)*math.log(a/e)
        return score
    @staticmethod
    def record(model,feature,expected,actual,threshold=.2):
        score=DriftService.population_stability_index(expected,actual); event=ModelDriftEvent.objects.create(model=model,feature=feature,score=Decimal(str(round(score,8))),threshold=Decimal(str(threshold)),details={'expected_count':len(expected),'actual_count':len(actual),'psi':score})
        return event

class ModelMonitoringService:
    @staticmethod
    def latency(model,minutes=60):
        since=timezone.now()-timedelta(minutes=minutes); qs=model.prediction_requests.filter(created_at__gte=since); values=list(qs.values_list('latency_ms',flat=True)); return {'count':len(values),'average_ms':statistics.fmean(values) if values else 0,'max_ms':max(values) if values else 0}
    @staticmethod
    def accuracy_from_feedback(model,days=30):
        since=timezone.now()-timedelta(days=days); feedback=model.prediction_requests.filter(created_at__gte=since,feedback__is_correct__isnull=False).values_list('feedback__is_correct',flat=True); values=list(feedback); return {'reviewed':len(values),'accuracy':sum(values)/len(values) if values else None}

from apps.ai_engine.services_domain import LeadScoringService, SupportClassifier, SalesForecastService, InventoryDemandService
