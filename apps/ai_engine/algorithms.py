"""Small, dependency-light algorithms used by EnterpriseOne's ML layer."""
import math
import random
from collections import defaultdict

class LinearRegressionModel:
    def __init__(self): self.weights=[]; self.bias=0.0
    def fit(self,X,y,learning_rate=.01,epochs=500):
        if not X:return self
        n=len(X); m=len(X[0]); self.weights=[0.0]*m
        for _ in range(epochs):
            gradients=[0.0]*m; bias_gradient=0.0
            for row,target in zip(X,y):
                pred=self.predict_one(row); error=pred-float(target)
                for j,value in enumerate(row): gradients[j]+=error*float(value)/n
                bias_gradient+=error/n
            self.weights=[w-learning_rate*g for w,g in zip(self.weights,gradients)]; self.bias-=learning_rate*bias_gradient
        return self
    def predict_one(self,row): return self.bias+sum(w*float(x) for w,x in zip(self.weights,row))
    def predict(self,X): return [self.predict_one(row) for row in X]

class LogisticRegressionModel:
    def __init__(self): self.weights=[]; self.bias=0.0
    @staticmethod
    def sigmoid(value):
        if value>=0:
            z=math.exp(-value); return 1/(1+z)
        z=math.exp(value); return z/(1+z)
    def fit(self,X,y,learning_rate=.05,epochs=500):
        if not X:return self
        m=len(X[0]); n=len(X); self.weights=[0.0]*m
        for _ in range(epochs):
            gw=[0.0]*m; gb=0.0
            for row,target in zip(X,y):
                p=self.sigmoid(self.bias+sum(w*float(x) for w,x in zip(self.weights,row))); error=p-float(target)
                for j,x in enumerate(row): gw[j]+=error*float(x)/n
                gb+=error/n
            self.weights=[w-learning_rate*g for w,g in zip(self.weights,gw)]; self.bias-=learning_rate*gb
        return self
    def predict_proba(self,X): return [self.sigmoid(self.bias+sum(w*float(x) for w,x in zip(self.weights,row))) for row in X]
    def predict(self,X,threshold=.5): return [int(p>=threshold) for p in self.predict_proba(X)]

class KMeansModel:
    def __init__(self,k=3,max_iter=100): self.k=k; self.max_iter=max_iter; self.centroids=[]
    @staticmethod
    def distance(a,b): return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))
    def fit(self,X):
        if not X:return self
        self.centroids=[list(map(float,row)) for row in X[:min(self.k,len(X))]]
        while len(self.centroids)<self.k:self.centroids.append(list(self.centroids[-1]))
        for _ in range(self.max_iter):
            groups=defaultdict(list)
            for row in X: groups[self.predict_one(row)].append(row)
            changed=False
            for idx in range(self.k):
                rows=groups.get(idx)
                if not rows:continue
                center=[sum(float(row[j]) for row in rows)/len(rows) for j in range(len(rows[0]))]
                if self.distance(center,self.centroids[idx])>1e-8:changed=True
                self.centroids[idx]=center
            if not changed:break
        return self
    def predict_one(self,row): return min(range(len(self.centroids)),key=lambda i:self.distance(row,self.centroids[i]))
    def predict(self,X): return [self.predict_one(row) for row in X]

class DecisionStump:
    def __init__(self): self.feature=0; self.threshold=0; self.left=0; self.right=1
    def fit(self,X,y):
        if not X:return self
        best=(float('inf'),0,0,1)
        for j in range(len(X[0])):
            thresholds=sorted({float(row[j]) for row in X})
            for threshold in thresholds:
                left=[target for row,target in zip(X,y) if float(row[j])<=threshold]; right=[target for row,target in zip(X,y) if float(row[j])>threshold]
                if not left or not right:continue
                lp=max(set(left),key=left.count); rp=max(set(right),key=right.count); error=sum(t!=lp for t in left)+sum(t!=rp for t in right)
                if error<best[0]:best=(error,j,threshold,lp,rp)
        if best[0]!=float('inf'):_,self.feature,self.threshold,self.left,self.right=best
        return self
    def predict(self,X): return [self.left if float(row[self.feature])<=self.threshold else self.right for row in X]

class MovingAverageModel:
    def __init__(self,window=3):self.window=window
    def fit(self,values):self.history=[float(v) for v in values];return self
    def predict(self,periods=1):
        history=list(getattr(self,'history',[])); out=[]
        for _ in range(periods):
            value=sum(history[-self.window:])/len(history[-self.window:]) if history else 0.0; history.append(value); out.append(value)
        return out

class ExponentialSmoothingModel:
    def __init__(self,alpha=.3):self.alpha=alpha;self.level=None
    def fit(self,values):
        values=[float(v) for v in values]
        if values:
            self.level=values[0]
            for value in values[1:]:self.level=self.alpha*value+(1-self.alpha)*self.level
        return self
    def predict(self,periods=1):return [self.level or 0.0]*periods
