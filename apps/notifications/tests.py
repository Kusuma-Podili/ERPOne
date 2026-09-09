from django.test import TestCase
from .services import TemplateRenderer
class NotificationServiceTests(TestCase):
    def test_template_renderer_supports_nested_values(self):
        self.assertEqual(TemplateRenderer.render('Hello {{ customer.name }}',{'customer':{'name':'A'}}),'Hello A')
    def test_missing_values_are_safe(self):
        self.assertEqual(TemplateRenderer.render('{{ missing }}',{}),'')
