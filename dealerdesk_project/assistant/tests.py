from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Dealer, Product
from assistant.agent import tool_search_parts, tool_check_stock, tool_create_draft_order


class AssistantToolTests(TestCase):
    def setUp(self):
        self.dealer = Dealer.objects.create(
            dealer_code="DLR-001",
            name="Test Dealer",
        )
        self.p1 = Product.objects.create(
            sku="BRK-1044",
            name="Brake Pad Set - Bajaj Pulsar 150",
            category="Brakes",
            brand="Endurance",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("1459.50"),
            stock=25,
            description="High quality disc brake pads.",
        )
        self.p2 = Product.objects.create(
            sku="CHN-1001",
            name="Chain Sprocket Kit - Bajaj Pulsar 150",
            category="Drivetrain",
            brand="Rolon",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("2100.00"),
            stock=12,
        )

    def test_search_parts_with_plural_stemming(self):
        # Query uses plural 'pads', catalogue has singular 'Pad'
        result = tool_search_parts(query="brake pads", vehicle="Pulsar 150")
        self.assertGreaterEqual(result["count"], 1)
        top = result["results"][0]
        self.assertEqual(top["sku"], "BRK-1044")
        self.assertEqual(top["price"], "1459.50")
        self.assertEqual(top["stock"], 25)

    def test_check_stock_tool(self):
        res1 = tool_check_stock("BRK-1044")
        self.assertEqual(res1["sku"], "BRK-1044")
        self.assertEqual(res1["stock"], 25)
        self.assertEqual(res1["price"], "1459.50")

        res2 = tool_check_stock("UNKNOWN-000")
        self.assertIn("error", res2)

    def test_create_draft_order_tool(self):
        res = tool_create_draft_order(
            dealer_id=self.dealer.id,
            items=[{"sku": "BRK-1044", "quantity": 2}],
        )
        self.assertIn("order_number", res)
        self.assertEqual(res["status"], "DRAFT")

        # Inventory is NOT touched by draft order
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 25)


class AssistantChatViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dealer = Dealer.objects.create(
            dealer_code="DLR-002",
            name="Second Dealer",
        )

    def test_chat_validation_missing_fields(self):
        r1 = self.client.post("/api/assistant/chat/", {"dealer_id": self.dealer.id}, format="json")
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()["error"]["code"], "VALIDATION_ERROR")

        r2 = self.client.post("/api/assistant/chat/", {
            "session_id": "test-1",
            "dealer_id": 99999,  # Unknown dealer
            "message": "Hello",
        }, format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.json()["error"]["code"], "VALIDATION_ERROR")

    def test_chat_schema_response(self):
        # Even without a configured GEMINI_API_KEY, the API must return 200 with the exact contract shape
        response = self.client.post("/api/assistant/chat/", {
            "session_id": "session-smoke",
            "dealer_id": self.dealer.id,
            "message": "Do you have brake pads?",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reply", data)
        self.assertIsInstance(data["reply"], str)
        self.assertIn("cited_skus", data)
        self.assertIsInstance(data["cited_skus"], list)
        self.assertIn("tool_calls", data)
        self.assertIsInstance(data["tool_calls"], list)
        self.assertIn("actions", data)
        self.assertIsInstance(data["actions"], list)
