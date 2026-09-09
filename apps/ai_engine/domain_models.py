"""Domain intelligence contracts used by application modules."""
from dataclasses import dataclass
from datetime import date

@dataclass
class SalesForecast:
    period:str; predicted_value:float; lower_bound:float; upper_bound:float; confidence:float=0.0
@dataclass
class CustomerScore:
    customer_id:str; score:float; segment:str; reasons:list
@dataclass
class InventoryForecast:
    item_id:str; expected_demand:float; reorder_point:float; safety_stock:float
@dataclass
class AnomalyFinding:
    source:str; record_id:str; score:float; severity:str; reasons:list
@dataclass
class SupportPrediction:
    ticket_id:str; category:str; priority:str; confidence:float

class ForecastConfidence:
    @staticmethod
    def interval(values,forecast,z=1.96):
        if not values:return (forecast,forecast)
        mean=sum(values)/len(values); variance=sum((v-mean)**2 for v in values)/len(values); spread=(variance**.5)*z; return forecast-spread,forecast+spread

class RiskScoring:
    @staticmethod
    def weighted(values,weights):
        total=0; weight_total=0
        for name,weight in weights.items():
            total+=max(0,min(100,float(values.get(name,0))))*weight; weight_total+=weight
        return total/weight_total if weight_total else 0
    @staticmethod
    def band(score):return 'critical' if score>=80 else 'high' if score>=60 else 'medium' if score>=35 else 'low'
