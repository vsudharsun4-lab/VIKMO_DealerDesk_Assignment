from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Dealer, Product


class ProductTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            sku="BRK-1044",
            name="Brake Pad Set - Bajaj Pulsar 150",
            category="Brakes",
            brand="Endurance",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("1459.50"),
            stock=50,
            description="High performance brake pads.",
        )

    def test_list_products_pagination(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["sku"], "BRK-1044")
        self.assertEqual(data["results"][0]["price"], "1459.50")
        self.assertEqual(data["results"][0]["stock"], 50)

    def test_product_filtering(self):
        # Search match
        r1 = self.client.get("/api/products/?search=Endurance")
        self.assertEqual(r1.json()["count"], 1)

        # Category match
        r2 = self.client.get("/api/products/?category=Brakes")
        self.assertEqual(r2.json()["count"], 1)

        # Vehicle substring
        r3 = self.client.get("/api/products/?vehicle=Pulsar")
        self.assertEqual(r3.json()["count"], 1)

        # Vehicle non-match
        r4 = self.client.get("/api/products/?vehicle=Splendor")
        self.assertEqual(r4.json()["count"], 0)

    def test_create_product(self):
        payload = {
            "sku": "FIL-9999",
            "name": "Oil Filter - Royal Enfield",
            "category": "Filters",
            "brand": "Mahle",
            "vehicle_fitment": "Royal Enfield Classic 350",
            "price": "450.00",
            "description": "OEM replacement",
        }
        response = self.client.post("/api/products/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["sku"], "FIL-9999")
        self.assertEqual(data["stock"], 0)
        self.assertEqual(data["price"], "450.00")

    def test_create_product_duplicate_sku(self):
        payload = {
            "sku": "BRK-1044",
            "name": "Another brake pad",
            "category": "Brakes",
            "brand": "Endurance",
            "vehicle_fitment": "Bajaj Pulsar 150",
            "price": "1200.00",
        }
        response = self.client.post("/api/products/", payload, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "DUPLICATE")

    def test_create_product_invalid_price(self):
        payload = {
            "sku": "TEST-01",
            "name": "Test Part",
            "category": "Test",
            "brand": "Test",
            "vehicle_fitment": "Universal",
            "price": "100.999",  # > 2 decimal places
        }
        response = self.client.post("/api/products/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_get_product_detail(self):
        r1 = self.client.get("/api/products/BRK-1044/")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["sku"], "BRK-1044")

        r2 = self.client.get("/api/products/NON-EXISTENT/")
        self.assertEqual(r2.status_code, 404)
        self.assertEqual(r2.json()["error"]["code"], "NOT_FOUND")

    def test_patch_product(self):
        response = self.client.patch("/api/products/BRK-1044/", {"price": "1599.00"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["price"], "1599.00")
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("1599.00"))


class InventoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            sku="BRK-1044",
            name="Brake Pad Set",
            category="Brakes",
            brand="Endurance",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("1459.50"),
            stock=10,
        )

    def test_update_inventory_success(self):
        response = self.client.put(
            "/api/inventory/BRK-1044/",
            {"quantity": 25, "reason": "stock count correction"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sku": "BRK-1044", "quantity": 25})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 25)

    def test_update_inventory_negative_quantity(self):
        response = self.client.put(
            "/api/inventory/BRK-1044/",
            {"quantity": -5, "reason": "bad quantity"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_update_inventory_unknown_sku(self):
        response = self.client.put(
            "/api/inventory/UNKNOWN-SKU/",
            {"quantity": 10, "reason": "unknown"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")


class DealerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dealer = Dealer.objects.create(
            dealer_code="DLR-007",
            name="Apex Motors",
            city="Bengaluru",
            credit_limit=Decimal("100000.00"),
        )

    def test_list_and_detail_dealers(self):
        r1 = self.client.get("/api/dealers/")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["count"], 1)

        r2 = self.client.get(f"/api/dealers/{self.dealer.id}/")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["dealer_code"], "DLR-007")
        self.assertEqual(r2.json()["credit_limit"], "100000.00")

    def test_create_dealer_success_and_duplicate(self):
        payload = {"dealer_code": "DLR-008", "name": "Speedway Auto"}
        r1 = self.client.post("/api/dealers/", payload, format="json")
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.json()["dealer_code"], "DLR-008")

        # Duplicate dealer_code
        r2 = self.client.post("/api/dealers/", payload, format="json")
        self.assertEqual(r2.status_code, 409)
        self.assertEqual(r2.json()["error"]["code"], "DUPLICATE")
