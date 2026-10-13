from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Dealer, Product


class CoreTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_seed_data_idempotency(self):
        # Run seed_data once
        call_command("seed_data")
        prod_count_1 = Product.objects.count()
        dealer_count_1 = Dealer.objects.count()

        self.assertEqual(prod_count_1, 600)
        self.assertEqual(dealer_count_1, 25)

        # Run seed_data a second time: must NOT create duplicates
        call_command("seed_data")
        prod_count_2 = Product.objects.count()
        dealer_count_2 = Dealer.objects.count()

        self.assertEqual(prod_count_1, prod_count_2)
        self.assertEqual(dealer_count_1, dealer_count_2)
