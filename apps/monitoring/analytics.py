"""Time-series analysis helpers used by monitoring dashboards and optimization jobs."""
import statistics
from datetime import timedelta


def moving_average(values, window=5):
    values = [float(v) for v in values]
    if window <= 0: raise ValueError("window must be positive")
    return [statistics.fmean(values[max(0, i-window+1):i+1]) for i in range(len(values))]


def exponential_smoothing(values, alpha=0.3):
    if not 0 < alpha <= 1: raise ValueError("alpha must be between 0 and 1")
    result=[]; level=None
    for value in values:
        level=float(value) if level is None else alpha*float(value)+(1-alpha)*level
        result.append(level)
    return result


def linear_trend(values):
    values=[float(v) for v in values]
    n=len(values)
    if n<2: return {"slope":0.0,"intercept":values[0] if values else 0.0,"direction":"FLAT"}
    x_mean=(n-1)/2
    y_mean=statistics.fmean(values)
    denom=sum((x-x_mean)**2 for x in range(n))
    slope=sum((x-x_mean)*(y-y_mean) for x,y in enumerate(values))/denom if denom else 0
    intercept=y_mean-slope*x_mean
    return {"slope":slope,"intercept":intercept,"direction":"UP" if slope>0 else "DOWN" if slope<0 else "FLAT"}


def anomaly_scores(values, window=10):
    values=[float(v) for v in values]; scores=[]
    for i,value in enumerate(values):
        baseline=values[max(0,i-window):i] or values[:i+1]
        mean=statistics.fmean(baseline)
        std=statistics.pstdev(baseline) if len(baseline)>1 else 0
        scores.append(abs(value-mean)/std if std else 0.0)
    return scores


def capacity_forecast(current, growth_rate, periods):
    current=float(current); growth=float(growth_rate); output=[]
    for period in range(1, periods+1):
        current*=1+growth; output.append({"period":period,"forecast":current})
    return output


def percentile(values, p):
    data=sorted(float(v) for v in values)
    if not data:return 0.0
    if len(data)==1:return data[0]
    position=(len(data)-1)*p/100
    lo=int(position); hi=min(lo+1,len(data)-1)
    return data[lo]+(data[hi]-data[lo])*(position-lo)
