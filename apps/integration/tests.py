from django.test import SimpleTestCase
from .services import Correlation, IdempotencyService, MappingEngine, RetryPolicy
class IntegrationUtilityTests(SimpleTestCase):
    def test_correlation_is_unique(self): self.assertNotEqual(Correlation.new(),Correlation.new())
    def test_idempotency_is_stable(self): self.assertEqual(IdempotencyService.key("x",{"a":1}),IdempotencyService.key("x",{"a":1}))
    def test_mapping(self):
        class M: field_map={"name":"customer_name"}; defaults={"active":True}; transforms={"name":"upper"}
        self.assertEqual(MappingEngine.transform({"customer_name":"kusuma"},M),{"active":True,"name":"KUSUMA"})
    def test_retry_backoff(self): self.assertGreater(RetryPolicy.next_attempt(3),RetryPolicy.next_attempt(1))
