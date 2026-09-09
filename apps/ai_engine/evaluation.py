import math
import statistics
from .services import ModelMath

class EvaluationReport:
    def __init__(self,problem_type,metrics,thresholds=None):self.problem_type=problem_type;self.metrics=metrics;self.thresholds=thresholds or {}
    @property
    def passed(self):return all(float(self.metrics.get(k,0))>=float(v) for k,v in self.thresholds.items())
    def to_dict(self):return {'problem_type':self.problem_type,'metrics':self.metrics,'thresholds':self.thresholds,'passed':self.passed}

class RegressionEvaluator:
    @staticmethod
    def evaluate(actual,predicted):
        return {'mae':ModelMath.mae(actual,predicted),'mse':ModelMath.mse(actual,predicted),'rmse':ModelMath.rmse(actual,predicted),'r2':ModelMath.r2(actual,predicted)}
    @staticmethod
    def residuals(actual,predicted):return [float(a)-float(p) for a,p in zip(actual,predicted)]
    @staticmethod
    def mean_residual(actual,predicted):
        values=RegressionEvaluator.residuals(actual,predicted);return statistics.fmean(values) if values else 0

class ClassificationEvaluator:
    @staticmethod
    def evaluate(actual,predicted):
        return {'accuracy':ModelMath.accuracy(actual,predicted),'precision':ModelMath.precision(actual,predicted),'recall':ModelMath.recall(actual,predicted),'f1':ModelMath.f1(actual,predicted)}
    @staticmethod
    def confusion_matrix(actual,predicted,labels=None):
        labels=labels or sorted(set(actual)|set(predicted)); return {str(a):{str(p):sum(x==a and y==p for x,y in zip(actual,predicted)) for p in labels} for a in labels}

class ForecastEvaluator:
    @staticmethod
    def evaluate(actual,predicted):
        errors=[float(a)-float(p) for a,p in zip(actual,predicted)]; mae=sum(abs(e) for e in errors)/len(errors) if errors else 0; rmse=math.sqrt(sum(e*e for e in errors)/len(errors)) if errors else 0; return {'mae':mae,'rmse':rmse,'bias':sum(errors)/len(errors) if errors else 0}

class ModelComparison:
    @staticmethod
    def rank(reports,metric,higher_is_better=True):return sorted(reports,key=lambda r:float(r.metrics.get(metric,0)),reverse=higher_is_better)
