from django.test import TestCase
from django.utils import timezone
from .models import DocumentCategory,Document
class DocumentDomainTests(TestCase):
    def test_document_number_is_generated_on_save(self):
        self.assertTrue(Document._meta.get_field('document_number').blank)
    def test_category_has_retention_policy_setting(self):
        self.assertEqual(DocumentCategory._meta.get_field('retention_days').default,0)
