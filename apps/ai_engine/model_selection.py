"""Model selection, cross validation and hyperparameter search helpers."""
import itertools
import math
import statistics
from .algorithms import LinearRegressionModel, LogisticRegressionModel
from .services import ModelMath

class KFold:
    def __init__(self,n_splits=5):
        if n_splits<2:raise ValueError('n_splits must be at least 2')
        self.n_splits=n_splits
    def split(self,X):
        n=len(X); fold_size=max(1,math.ceil(n/self.n_splits));
        for start in range(0,n,fold_size):yield list(range(0,start))+list(range(min(n,start+fold_size),n)),list(range(start,min(n,start+fold_size)))

class CrossValidator:
    @staticmethod
    def regression(model_factory,X,y,n_splits=5):
        scores=[]
        for train_idx,test_idx in KFold(n_splits).split(X):
            model=model_factory().fit([X[i] for i in train_idx],[y[i] for i in train_idx]); pred=model.predict([X[i] for i in test_idx]); scores.append(ModelMath.r2([y[i] for i in test_idx],pred))
        return {'fold_scores':scores,'mean':statistics.fmean(scores) if scores else 0,'std':statistics.pstdev(scores) if len(scores)>1 else 0}
    @staticmethod
    def classification(model_factory,X,y,n_splits=5):
        scores=[]
        for train_idx,test_idx in KFold(n_splits).split(X):
            model=model_factory().fit([X[i] for i in train_idx],[y[i] for i in train_idx]); pred=model.predict([X[i] for i in test_idx]); scores.append(ModelMath.accuracy([y[i] for i in test_idx],pred))
        return {'fold_scores':scores,'mean':statistics.fmean(scores) if scores else 0,'std':statistics.pstdev(scores) if len(scores)>1 else 0}

class GridSearch:
    @staticmethod
    def combinations(grid):
        keys=list(grid); values=[grid[k] for k in keys]; return [dict(zip(keys,combo)) for combo in itertools.product(*values)]
    @classmethod
    def linear_regression(cls,X,y,learning_rates=(.001,.01,.05),epochs=(100,300)):
        results=[]
        for params in cls.combinations({'learning_rate':learning_rates,'epochs':epochs}):
            model=LinearRegressionModel().fit(X,y,**params); pred=model.predict(X); results.append({'parameters':params,'r2':ModelMath.r2(y,pred),'mae':ModelMath.mae(y,pred)})
        return max(results,key=lambda r:r['r2']) if results else None
    @classmethod
    def logistic_regression(cls,X,y,learning_rates=(.01,.05,.1),epochs=(100,300)):
        results=[]
        for params in cls.combinations({'learning_rate':learning_rates,'epochs':epochs}):
            model=LogisticRegressionModel().fit(X,y,**params); pred=model.predict(X); results.append({'parameters':params,'accuracy':ModelMath.accuracy(y,pred),'f1':ModelMath.f1(y,pred)})
        return max(results,key=lambda r:r['f1']) if results else None

class ThresholdOptimizer:
    @staticmethod
    def classification(actual,probabilities):
        candidates=[]
        for threshold in [i/100 for i in range(10,91,5)]:
            predicted=[int(p>=threshold) for p in probabilities]; candidates.append({'threshold':threshold,'f1':ModelMath.f1(actual,predicted),'accuracy':ModelMath.accuracy(actual,predicted)})
        return max(candidates,key=lambda x:x['f1']) if candidates else None
