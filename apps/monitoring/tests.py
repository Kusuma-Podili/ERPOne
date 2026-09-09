"""Fast, dependency-light behavioral tests for monitoring algorithms."""
import unittest
from .analytics import moving_average, exponential_smoothing, linear_trend, anomaly_scores, capacity_forecast, percentile
from .optimization import OptimizationEngine

class MonitoringAnalyticsTests(unittest.TestCase):
    def test_moving_average(self): self.assertEqual(moving_average([1,2,3],2),[1.0,1.5,2.5])
    def test_smoothing(self): self.assertAlmostEqual(exponential_smoothing([10,20],0.5)[-1],15)
    def test_trend(self): self.assertEqual(linear_trend([1,2,3])["direction"],"UP")
    def test_anomaly_score_shape(self): self.assertEqual(len(anomaly_scores([1,1,10])),3)
    def test_capacity_forecast(self): self.assertEqual(len(capacity_forecast(100,.1,4)),4)
    def test_percentile(self): self.assertEqual(percentile([1,2,3,4],50),2.5)

class OptimizationTests(unittest.TestCase):
    def setUp(self): self.engine=OptimizationEngine()
    def test_latency_signal(self): self.assertIsNotNone(self.engine.latency_signal([100,120,150],100))
    def test_error_signal(self): self.assertIsNotNone(self.engine.error_signal(3,100,1))
    def test_capacity_signal(self): self.assertEqual(self.engine.capacity_signal(96)["priority"],1)
    def test_summary(self): self.assertEqual(self.engine.summarize([])["count"],0)
