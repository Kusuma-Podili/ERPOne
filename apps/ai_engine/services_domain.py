from decimal import Decimal
from django.db.models import Avg, Count, Sum
from apps.ai_engine.services import FeatureEngineering, ForecastingService, ModelMath

class SalesForecastService:
    @staticmethod
    def forecast_from_orders(orders, periods=6):
        amounts=list(orders.values_list('total_amount',flat=True))
        return ForecastingService.moving_average_forecast(amounts,periods=periods)

class InventoryDemandService:
    @staticmethod
    def demand_summary(queryset, quantity_field='quantity'):
        total=queryset.aggregate(total=Sum(quantity_field))['total'] or 0
        count=queryset.aggregate(count=Count('id'))['count'] or 0
        return {'observations':count,'total_demand':total,'average_demand':float(total/count) if count else 0}

class CustomerSegmentationService:
    @staticmethod
    def rfm_score(rows):
        if not rows:return []
        recency=[FeatureEngineering.numeric(r.get('recency')) for r in rows]; frequency=[FeatureEngineering.numeric(r.get('frequency')) for r in rows]; monetary=[FeatureEngineering.numeric(r.get('monetary')) for r in rows]
        def rank(values,value):
            ordered=sorted(values); return min(5,max(1,int((ordered.index(value)+1)/len(ordered)*5)))
        return [dict(row,recency_score=rank(recency,row.get('recency')),frequency_score=rank(frequency,row.get('frequency')),monetary_score=rank(monetary,row.get('monetary'))) for row in rows]

class FraudAnomalyService:
    @staticmethod
    def score(values, z_threshold=3):
        nums=[FeatureEngineering.numeric(v) for v in values]; result=[]
        mean=sum(nums)/len(nums) if nums else 0; variance=sum((v-mean)**2 for v in nums)/len(nums) if nums else 0; std=variance**.5 or 1
        for value in nums: result.append({'value':value,'z_score':abs(value-mean)/std,'anomaly':abs(value-mean)/std>=z_threshold})
        return result

class LeadScoringService:
    WEIGHTS={'company_size':.15,'engagement':.30,'budget':.25,'fit':.20,'recency':.10}
    @classmethod
    def score(cls, features):
        score=0
        for key,weight in cls.WEIGHTS.items(): score+=min(100,max(0,FeatureEngineering.numeric(features.get(key))))*weight
        return round(score,2)

class SupportClassifier:
    KEYWORDS={'billing':['invoice','payment','charge','bill'],'technical':['error','bug','login','broken'],'delivery':['delivery','shipment','late'],'account':['password','profile','account']}
    @classmethod
    def classify(cls,text):
        text=(text or '').lower(); scores={k:sum(text.count(word) for word in words) for k,words in cls.KEYWORDS.items()}; category=max(scores,key=scores.get) if scores and max(scores.values()) else 'general'; return {'category':category,'confidence':round(scores.get(category,0)/max(1,sum(scores.values())),2)}

class FinancialAnomalyService:
    @staticmethod
    def detect(values, sensitivity=2.5): return FraudAnomalyService.score(values,sensitivity)
