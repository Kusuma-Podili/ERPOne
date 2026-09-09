import math

class FeatureContribution:
    @staticmethod
    def linear(weights,features,baseline=0.0):
        result=[]
        for name,value in features.items():
            weight=float(weights.get(name,0)); contribution=weight*float(value); result.append({'feature':name,'value':value,'weight':weight,'contribution':contribution})
        result.sort(key=lambda item:abs(item['contribution']),reverse=True); return {'baseline':baseline,'contributions':result,'total_contribution':sum(x['contribution'] for x in result)}

class PredictionExplanation:
    def __init__(self,prediction,contributions,method='linear'):self.prediction=prediction;self.contributions=contributions;self.method=method
    def top_features(self,limit=5):return self.contributions[:limit]
    def to_dict(self):return {'prediction':self.prediction,'method':self.method,'top_features':self.top_features()}

class SensitivityAnalyzer:
    @staticmethod
    def one_at_a_time(predictor,features,step=.1):
        baseline=float(predictor(features)); changes=[]
        for name,value in features.items():
            try:
                altered=dict(features); altered[name]=float(value)*(1+step); new=float(predictor(altered)); changes.append({'feature':name,'baseline':baseline,'altered':new,'delta':new-baseline})
            except (TypeError,ValueError):continue
        return sorted(changes,key=lambda x:abs(x['delta']),reverse=True)
