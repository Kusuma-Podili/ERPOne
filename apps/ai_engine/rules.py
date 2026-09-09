"""Business-facing AI decision rules that can consume model outputs."""
from dataclasses import dataclass

@dataclass
class RuleResult:
    rule:str; matched:bool; action:str; reason:str; metadata:dict

class DecisionRule:
    name='rule'
    def evaluate(self,prediction,context=None):raise NotImplementedError

class HighValueTransactionRule(DecisionRule):
    name='high_value_transaction'
    def __init__(self,limit=100000):self.limit=limit
    def evaluate(self,prediction,context=None):
        value=float((context or {}).get('amount',0)); matched=value>=self.limit; return RuleResult(self.name,matched,'manual_review' if matched else 'approve','Amount threshold evaluated',{'amount':value,'limit':self.limit})

class CustomerChurnRule(DecisionRule):
    name='customer_churn'
    def __init__(self,threshold=.7):self.threshold=threshold
    def evaluate(self,prediction,context=None):
        score=float(prediction.get('probability',prediction.get('score',0))); matched=score>=self.threshold; return RuleResult(self.name,matched,'retention_campaign' if matched else 'standard_followup','Churn probability evaluated',{'score':score,'threshold':self.threshold})

class InventoryRiskRule(DecisionRule):
    name='inventory_risk'
    def __init__(self,coverage_days=7):self.coverage_days=coverage_days
    def evaluate(self,prediction,context=None):
        stock=float((context or {}).get('stock',0)); demand=float((context or {}).get('daily_demand',0)); days=stock/demand if demand else 999; matched=days<=self.coverage_days; return RuleResult(self.name,matched,'create_replenishment' if matched else 'monitor','Stock coverage evaluated',{'coverage_days':days})

class RuleEngine:
    def __init__(self,rules=None):self.rules=rules or []
    def add(self,rule):self.rules.append(rule);return self
    def evaluate(self,prediction,context=None):return [rule.evaluate(prediction,context) for rule in self.rules]
    def actions(self,prediction,context=None):return [r.action for r in self.evaluate(prediction,context) if r.matched]
