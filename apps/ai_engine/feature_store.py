"""In-process feature store contracts for repeatable model features."""
from dataclasses import dataclass,field
from datetime import datetime,timedelta
from .services import FeatureEngineering

@dataclass
class FeatureValue:
    entity_id:str; feature:str; value:object; observed_at:datetime; metadata:dict=field(default_factory=dict)

class FeatureStore:
    def __init__(self):self._values={}
    def put(self,entity_id,feature,value,observed_at=None,metadata=None):
        item=FeatureValue(str(entity_id),feature,value,observed_at or datetime.utcnow(),metadata or {}); self._values[(item.entity_id,feature)]=item; return item
    def get(self,entity_id,feature,default=None):
        item=self._values.get((str(entity_id),feature)); return item.value if item else default
    def get_record(self,entity_id,features):return {feature:self.get(entity_id,feature) for feature in features}
    def history(self,entity_id,feature):return [v for (eid,name),v in self._values.items() if eid==str(entity_id) and name==feature]
    def snapshot(self,entity_id,features):return {'entity_id':str(entity_id),'features':self.get_record(entity_id,features)}

class FeatureCache:
    def __init__(self,ttl_seconds=300):self.ttl=ttl_seconds;self._items={}
    def set(self,key,value,now=None):self._items[key]=(value,now or datetime.utcnow())
    def get(self,key,now=None):
        item=self._items.get(key)
        if not item:return None
        current=now or datetime.utcnow()
        if current-item[1]>timedelta(seconds=self.ttl):self._items.pop(key,None);return None
        return item[0]
    def invalidate(self,key):self._items.pop(key,None)
    def clear(self):self._items.clear()

class FeaturePipelineBuilder:
    def __init__(self):self.steps=[]
    def numeric(self,*fields):self.steps.append(('numeric',fields));return self
    def normalize(self,*fields):self.steps.append(('normalize',fields));return self
    def derive(self,name,function):self.steps.append(('derive',name,function));return self
    def transform(self,row):
        output=dict(row)
        for step in self.steps:
            if step[0]=='numeric':
                for field in step[1]:output[field]=FeatureEngineering.numeric(output.get(field))
            elif step[0]=='normalize':
                for field in step[1]:output[field]=FeatureEngineering.numeric(output.get(field))
            elif step[0]=='derive':output[step[1]]=step[2](output)
        return output
