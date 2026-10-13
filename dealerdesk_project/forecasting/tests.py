from decimal import Decimal
import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Product
from forecasting.views import FORECAST_WEEKS, _load_forecast


class ForecastApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            sku="FIL-1012",
            name="Air Filter",
            category="Filters",
            brand="Mahle",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("450.00"),
            stock=40,
        )

    def test_forecast_detail_success(self):
        forecast_data = _load_forecast()
        if not forecast_data:
            self.skipTest("ml/forecast.csv not loaded")
        test_sku = list(forecast_data.keys())[0]

        response = self.client.get(f"/api/forecast/{test_sku}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sku"], test_sku)
        self.assertEqual(len(data["forecast"]), 4)
        weeks = [f["week_start"] for f in data["forecast"]]
        self.assertEqual(weeks, FORECAST_WEEKS)

    def test_forecast_detail_unknown_sku(self):
        response = self.client.get("/api/forecast/UNKNOWN-9999/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_reorder_suggestions(self):
        response = self.client.get("/api/reorder-suggestions/")
        self.assertEqual(response.status_code, 200)
        results = response.json().get("results")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 40)

        entry = results[0]
        for field in ("sku", "current_stock", "lead_time_weeks", "lead_time_demand", "safety_stock", "reorder_point", "reorder_qty"):
            self.assertIn(field, entry)

        self.assertGreaterEqual(entry["lead_time_weeks"], 1)
        self.assertGreaterEqual(entry["safety_stock"], 0)
        self.assertGreaterEqual(entry["reorder_qty"], 0)


class SupplierSyncTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("forecasting.sync_views.requests.Session")
    def test_supplier_sync_dedup_and_stock_untouched(self, mock_session_cls):
        # Create an existing product with local stock 50
        Product.objects.create(
            sku="BRK-1044",
            name="Old Name",
            category="Brakes",
            brand="Endurance",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("1200.00"),
            stock=50,
            description="Old description",
        )

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # Mock supplier returning two items: one older, one newer for same SKU, and an invalid item
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "supplier_sku": "SUP-1",
                    "sku": "BRK-1044",
                    "name": "Updated Name v1",
                    "category": "Brakes",
                    "brand": "Endurance",
                    "vehicle_fitment": "Bajaj Pulsar 150",
                    "price": "1400.00",
                    "supplier_stock": 200,
                    "updated_at": "2026-10-01T10:00:00Z",
                },
                {
                    "supplier_sku": "SUP-2",
                    "sku": "BRK-1044",
                    "name": "Updated Name v2 Latest",
                    "category": "Brakes",
                    "brand": "Endurance",
                    "vehicle_fitment": "Bajaj Pulsar 150",
                    "price": "1450.00",
                    "supplier_stock": 350,
                    "updated_at": "2026-10-05T10:00:00Z",
                },
                {
                    "supplier_sku": "SUP-INV",
                    "sku": "INV-001",
                    "name": "Invalid Part",
                    "price": "-10.00",  # Invalid price
                    "supplier_stock": 10,
                },
            ],
            "next_cursor": None,
        }
        mock_session.get.return_value = mock_response

        response = self.client.post("/api/sync/supplier/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["updated"], 1)
        self.assertEqual(data["created"], 0)
        self.assertEqual(len(data["rejected"]), 1)
        self.assertEqual(data["rejected"][0]["supplier_sku"], "SUP-INV")

        # Verify our local stock remained untouched at 50, but name & price updated to v2
        prod = Product.objects.get(sku="BRK-1044")
        self.assertEqual(prod.stock, 50)
        self.assertEqual(prod.name, "Updated Name v2 Latest")
        self.assertEqual(prod.price, Decimal("1450.00"))
