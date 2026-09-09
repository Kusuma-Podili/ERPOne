"""Read-only data adapter contracts for domain-specific ML datasets."""
from collections import defaultdict

class DatasetAdapter:
    source='generic'
    def __init__(self,organization):self.organization=organization
    def rows(self,limit=1000):raise NotImplementedError

class QueryAdapter(DatasetAdapter):
    def __init__(self,organization,queryset,fields=None):super().__init__(organization);self.queryset=queryset;self.fields=fields
    def rows(self,limit=1000):
        qs=self.queryset
        return list(qs.values(*(self.fields or []))[:limit]) if self.fields else list(qs.values()[:limit])

class SalesAdapter(QueryAdapter):
    source='sales'
class InventoryAdapter(QueryAdapter):
    source='inventory'
class FinanceAdapter(QueryAdapter):
    source='finance'
class CRMAdapter(QueryAdapter):
    source='crm'
class HRAdapter(QueryAdapter):
    source='hr'
class PayrollAdapter(QueryAdapter):
    source='payroll'
class ProjectAdapter(QueryAdapter):
    source='projects'
class SupportAdapter(QueryAdapter):
    source='support'

class DatasetProfiler:
    @staticmethod
    def profile(rows):
        if not rows:return {'row_count':0,'columns':{}}
        columns=sorted({key for row in rows for key in row}); result={'row_count':len(rows),'columns':{}}
        for column in columns:
            values=[row.get(column) for row in rows]; non_null=[v for v in values if v is not None]; numeric=[v for v in non_null if isinstance(v,(int,float))];
            result['columns'][column]={'type':type(non_null[0]).__name__ if non_null else 'unknown','null_count':len(values)-len(non_null),'unique_count':len({repr(v) for v in non_null}),'numeric':bool(numeric)}
            if numeric:result['columns'][column].update({'min':min(numeric),'max':max(numeric),'mean':sum(numeric)/len(numeric)})
        return result
    @staticmethod
    def quality_score(profile):
        if not profile['columns']:return 0
        scores=[]
        for data in profile['columns'].values():scores.append(max(0,1-data['null_count']/max(1,profile['row_count'])))
        return round(sum(scores)/len(scores)*100,2)
