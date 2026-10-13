from decimal import Decimal
import re
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Dealer, Product
from orders.models import Order


class OrderTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dealer = Dealer.objects.create(
            dealer_code="DLR-001",
            name="Bangalore Spares",
            credit_limit=Decimal("50000.00"),
        )
        self.p1 = Product.objects.create(
            sku="BRK-1044",
            name="Brake Pad Set",
            category="Brakes",
            brand="Endurance",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("1459.50"),
            stock=10,
        )
        self.p2 = Product.objects.create(
            sku="OIL-1001",
            name="Coolant 1L",
            category="Engine & Oils",
            brand="Motul",
            vehicle_fitment="Universal",
            price=Decimal("604.25"),
            stock=20,
        )

    def test_create_draft_order_and_gst_calculation(self):
        # 3 * 1459.50 = 4378.50, tax = 4378.50 * 0.18 = 788.13, total = 5166.63
        # 1 * 604.25 = 604.25, tax = 604.25 * 0.18 = 108.765 -> 108.77 (ROUND_HALF_UP), total = 713.02
        # subtotal = 4982.75, tax_total = 896.90, grand_total = 5879.65
        payload = {
            "dealer_id": self.dealer.id,
            "items": [
                {"sku": "BRK-1044", "quantity": 3},
                {"sku": "OIL-1001", "quantity": 1},
            ],
        }
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()

        self.assertEqual(data["status"], "DRAFT")
        self.assertTrue(re.match(r"^ORD-\d{8}-\d{4}$", data["order_number"]))
        self.assertEqual(data["subtotal"], "4982.75")
        self.assertEqual(data["tax_total"], "896.90")
        self.assertEqual(data["grand_total"], "5879.65")

        # Check line details
        items = data["items"]
        self.assertEqual(len(items), 2)
        it1 = next(i for i in items if i["sku"] == "BRK-1044")
        self.assertEqual(it1["unit_price"], "1459.50")
        self.assertEqual(it1["line_subtotal"], "4378.50")
        self.assertEqual(it1["line_tax"], "788.13")
        self.assertEqual(it1["line_total"], "5166.63")

        it2 = next(i for i in items if i["sku"] == "OIL-1001")
        self.assertEqual(it2["unit_price"], "604.25")
        self.assertEqual(it2["line_subtotal"], "604.25")
        self.assertEqual(it2["line_tax"], "108.77")  # 108.765 rounded half-up
        self.assertEqual(it2["line_total"], "713.02")

        # Draft order does not deduct stock
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)

    def test_create_order_validations(self):
        # Empty items
        r1 = self.client.post("/api/orders/", {"dealer_id": self.dealer.id, "items": []}, format="json")
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()["error"]["code"], "VALIDATION_ERROR")

        # Duplicate SKU in line items
        r2 = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "BRK-1044", "quantity": 1}, {"sku": "BRK-1044", "quantity": 2}],
        }, format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.json()["error"]["code"], "VALIDATION_ERROR")

        # Unknown SKU
        r3 = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "NOPE-0000", "quantity": 1}],
        }, format="json")
        self.assertEqual(r3.status_code, 400)
        self.assertEqual(r3.json()["error"]["code"], "VALIDATION_ERROR")

        # Unknown Dealer
        r4 = self.client.post("/api/orders/", {
            "dealer_id": 99999,
            "items": [{"sku": "BRK-1044", "quantity": 1}],
        }, format="json")
        self.assertEqual(r4.status_code, 400)
        self.assertEqual(r4.json()["error"]["code"], "VALIDATION_ERROR")

        # Invalid quantity
        r5 = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "BRK-1044", "quantity": 0}],
        }, format="json")
        self.assertEqual(r5.status_code, 400)

    def test_order_confirm_and_stock_deduction(self):
        resp = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "BRK-1044", "quantity": 4}],
        }, format="json")
        order_num = resp.json()["order_number"]

        # Confirm
        c_resp = self.client.post(f"/api/orders/{order_num}/confirm/")
        self.assertEqual(c_resp.status_code, 200)
        self.assertEqual(c_resp.json()["status"], "CONFIRMED")

        # Stock deducted from 10 to 6
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 6)

    def test_insufficient_stock_fails_all_or_nothing(self):
        resp = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [
                {"sku": "BRK-1044", "quantity": 15},  # only 10 available
                {"sku": "OIL-1001", "quantity": 2},   # 20 available
            ],
        }, format="json")
        order_num = resp.json()["order_number"]

        c_resp = self.client.post(f"/api/orders/{order_num}/confirm/")
        self.assertEqual(c_resp.status_code, 409)
        err = c_resp.json()["error"]
        self.assertEqual(err["code"], "INSUFFICIENT_STOCK")
        self.assertEqual(len(err["details"]), 1)
        self.assertEqual(err["details"][0]["sku"], "BRK-1044")
        self.assertEqual(err["details"][0]["requested"], 15)
        self.assertEqual(err["details"][0]["available"], 10)

        # Neither stock was changed
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)
        self.assertEqual(self.p2.stock, 20)

    def test_order_full_lifecycle(self):
        resp = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "BRK-1044", "quantity": 2}],
        }, format="json")
        order_num = resp.json()["order_number"]

        # Confirm: DRAFT -> CONFIRMED
        r_conf = self.client.post(f"/api/orders/{order_num}/confirm/")
        self.assertEqual(r_conf.status_code, 200)
        self.assertEqual(r_conf.json()["status"], "CONFIRMED")

        # Dispatch: CONFIRMED -> DISPATCHED
        r_disp = self.client.post(f"/api/orders/{order_num}/dispatch/")
        self.assertEqual(r_disp.status_code, 200)
        self.assertEqual(r_disp.json()["status"], "DISPATCHED")

        # Deliver: DISPATCHED -> DELIVERED
        r_del = self.client.post(f"/api/orders/{order_num}/deliver/")
        self.assertEqual(r_del.status_code, 200)
        self.assertEqual(r_del.json()["status"], "DELIVERED")

        # Attempt cancel on DELIVERED -> 409 INVALID_TRANSITION
        r_bad_cancel = self.client.post(f"/api/orders/{order_num}/cancel/")
        self.assertEqual(r_bad_cancel.status_code, 409)
        self.assertEqual(r_bad_cancel.json()["error"]["code"], "INVALID_TRANSITION")

    def test_cancel_confirmed_order_restores_stock_exactly_once(self):
        resp = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "BRK-1044", "quantity": 3}],
        }, format="json")
        order_num = resp.json()["order_number"]

        # Confirm: stock 10 -> 7
        self.client.post(f"/api/orders/{order_num}/confirm/")
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 7)

        # Cancel: stock restored 7 -> 10
        r_cancel = self.client.post(f"/api/orders/{order_num}/cancel/")
        self.assertEqual(r_cancel.status_code, 200)
        self.assertEqual(r_cancel.json()["status"], "CANCELLED")
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)

        # Second cancel is rejected
        r_second = self.client.post(f"/api/orders/{order_num}/cancel/")
        self.assertEqual(r_second.status_code, 409)
        self.assertEqual(r_second.json()["error"]["code"], "INVALID_TRANSITION")
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)

    def test_edit_order_items_and_order_locked(self):
        resp = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "BRK-1044", "quantity": 1}],
        }, format="json")
        order_num = resp.json()["order_number"]

        # PUT replaces items
        r_edit = self.client.put(f"/api/orders/{order_num}/", {
            "items": [{"sku": "OIL-1001", "quantity": 2}],
        }, format="json")
        self.assertEqual(r_edit.status_code, 200)
        self.assertEqual(len(r_edit.json()["items"]), 1)
        self.assertEqual(r_edit.json()["items"][0]["sku"], "OIL-1001")

        # Confirm locks order
        self.client.post(f"/api/orders/{order_num}/confirm/")

        # Attempt edit when confirmed -> 409 ORDER_LOCKED
        r_locked = self.client.put(f"/api/orders/{order_num}/", {
            "items": [{"sku": "BRK-1044", "quantity": 2}],
        }, format="json")
        self.assertEqual(r_locked.status_code, 409)
        self.assertEqual(r_locked.json()["error"]["code"], "ORDER_LOCKED")

    def test_idempotency_key_handling(self):
        payload = {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "BRK-1044", "quantity": 2}],
        }
        # First request with key
        r1 = self.client.post("/api/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="key-123")
        self.assertEqual(r1.status_code, 201)
        order_num = r1.json()["order_number"]

        # Second identical request returns original order
        r2 = self.client.post("/api/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="key-123")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["order_number"], order_num)

        # Third request with same key but different body -> 409 IDEMPOTENCY_CONFLICT
        diff_payload = {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "BRK-1044", "quantity": 5}],
        }
        r3 = self.client.post("/api/orders/", diff_payload, format="json", HTTP_IDEMPOTENCY_KEY="key-123")
        self.assertEqual(r3.status_code, 409)
        self.assertEqual(r3.json()["error"]["code"], "IDEMPOTENCY_CONFLICT")
