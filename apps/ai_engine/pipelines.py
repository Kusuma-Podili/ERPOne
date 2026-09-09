"""Composable ML data pipeline primitives."""
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Any
from .services import FeatureEngineering

@dataclass
class PipelineContext:
    rows:list[dict]=field(default_factory=list); metadata:dict=field(default_factory=dict); errors:list[str]=field(default_factory=list)

class PipelineStep:
    name='base'
    def run(self,context): return context

class ValidateColumnsStep(PipelineStep):
    name='validate_columns'
    def __init__(self,required):self.required=required
    def run(self,context):
        for index,row in enumerate(context.rows):
            missing=[c for c in self.required if c not in row]
            if missing:context.errors.append(f'row {index}: missing {missing}')
        context.metadata['validated_rows']=len(context.rows); return context

class DropNullRowsStep(PipelineStep):
    name='drop_null_rows'
    def __init__(self,columns):self.columns=columns
    def run(self,context):
        before=len(context.rows); context.rows=[r for r in context.rows if all(r.get(c) not in (None,'') for c in self.columns)]; context.metadata['dropped_null_rows']=before-len(context.rows); return context

class NumericTransformStep(PipelineStep):
    name='numeric_transform'
    def __init__(self,columns):self.columns=columns
    def run(self,context):
        for row in context.rows:
            for column in self.columns:row[column]=FeatureEngineering.numeric(row.get(column))
        return context

class NormalizeStep(PipelineStep):
    name='normalize'
    def __init__(self,columns):self.columns=columns
    def run(self,context):
        for column in self.columns:
            values=[row.get(column) for row in context.rows]; normalized=FeatureEngineering.normalize(values)
            for row,value in zip(context.rows,normalized):row[column]=value
        return context

class EncodeCategoricalStep(PipelineStep):
    name='encode_categorical'
    def __init__(self,columns):self.columns=columns
    def run(self,context):
        for column in self.columns:
            values=[row.get(column) for row in context.rows]; encoded=FeatureEngineering.one_hot(values)
            for row,value in zip(context.rows,encoded):row[f'{column}_encoded']=value
        return context

class AddDerivedFeatureStep(PipelineStep):
    name='derived_feature'
    def __init__(self,name,formula):self.feature_name=name;self.formula=formula
    def run(self,context):
        for row in context.rows:
            try:row[self.feature_name]=self.formula(row)
            except Exception as exc:context.errors.append(f'{self.feature_name}: {exc}')
        return context

class DatasetFingerprintStep(PipelineStep):
    name='fingerprint'
    def run(self,context):
        payload=repr(sorted(tuple(sorted(r.items())) for r in context.rows)).encode(); context.metadata['checksum']=sha256(payload).hexdigest(); context.metadata['fingerprinted_at']=datetime.utcnow().isoformat(); return context

class SplitStep(PipelineStep):
    name='split'
    def __init__(self,validation_ratio=.2):self.validation_ratio=validation_ratio
    def run(self,context):
        cut=int(len(context.rows)*(1-self.validation_ratio)); context.metadata['training_rows']=context.rows[:cut]; context.metadata['validation_rows']=context.rows[cut:]; return context

class MLDataPipeline:
    def __init__(self,steps=None):self.steps=steps or []
    def add(self,step):self.steps.append(step);return self
    def run(self,rows,metadata=None):
        context=PipelineContext(rows=[dict(r) for r in rows],metadata=metadata or {})
        for step in self.steps:context=step.run(context)
        context.metadata['row_count']=len(context.rows); context.metadata['steps']=[s.name for s in self.steps]; return context
