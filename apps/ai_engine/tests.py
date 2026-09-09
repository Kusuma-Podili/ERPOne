from decimal import Decimal
from django.test import SimpleTestCase
from .services import FeatureEngineering, ModelMath, BaselinePredictor, ForecastingService, DriftService, LeadScoringService, SupportClassifier

class FeatureEngineeringTests(SimpleTestCase):
    def test_normalize(self): self.assertEqual(FeatureEngineering.normalize([10,20,30]),[0.0,.5,1.0])
    def test_standardize(self): self.assertAlmostEqual(sum(FeatureEngineering.standardize([1,2,3])),0)
    def test_one_hot(self): self.assertEqual(FeatureEngineering.one_hot(['a','b'])[0],{'a':1,'b':0})
    def test_ratio(self): self.assertEqual(FeatureEngineering.safe_ratio(10,4),2.5)

class ModelMathTests(SimpleTestCase):
    def test_regression_metrics(self):
        self.assertEqual(ModelMath.mae([1,2],[1,4]),1.0); self.assertEqual(ModelMath.mse([1,2],[1,4]),2.0)
    def test_classification_metrics(self):
        self.assertEqual(ModelMath.accuracy([1,0,1],[1,1,1]),2/3); self.assertEqual(ModelMath.precision([1,0],[1,1]),.5)

class BaselineTests(SimpleTestCase):
    def test_forecast(self): self.assertEqual(BaselinePredictor.forecast([10,20,30],2),[40,50])
    def test_classification(self): self.assertEqual(BaselinePredictor.classification(['a','a','b']),'a')
    def test_anomaly(self): self.assertEqual(len(BaselinePredictor.anomaly([1,2,3])),3)

class DomainIntelligenceTests(SimpleTestCase):
    def test_lead_score(self): self.assertGreater(LeadScoringService.score({'fit':100,'budget':100,'engagement':100,'company_size':100,'recency':100}),99)
    def test_support_classifier(self): self.assertEqual(SupportClassifier.classify('invoice payment problem')['category'],'billing')
    def test_drift(self): self.assertGreaterEqual(DriftService.population_stability_index([1,2,3],[1,2,3]),0)

class ForecastingTests(SimpleTestCase):
    def test_moving_average(self): self.assertEqual(len(ForecastingService.moving_average_forecast([10,20,30],3)),3)
