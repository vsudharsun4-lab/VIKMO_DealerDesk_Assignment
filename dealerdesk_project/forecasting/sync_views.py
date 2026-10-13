"""Supplier sync view — §8 (bonus for AI/ML track).

POST /api/sync/supplier/

Fetches every page from the supplier API, handles rate limits (429 + Retry-After),
transient 5xx errors (up to 5 attempts per request), and applies the dedup/apply rules.
"""
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product


MAX_ATTEMPTS = 5
PAGE_LIMIT = 20


def _validate_item(item):
    """Return None if valid, or a reason string if invalid."""
    sku = (item.get("sku") or "").strip()
    if not sku:
        return "missing or empty sku"
    price_str = str(item.get("price", "")).strip()
    try:
        price = Decimal(price_str)
    except InvalidOperation:
        return f"invalid price: {price_str!r}"
    if price <= 0:
        return "price must be > 0"
    if price.as_tuple().exponent < -2:
        return "price has more than 2 decimal places"
    return None


def _fetch_page(session, url, key, cursor, requests_made):
    """Fetch one page with retry logic. Returns (data, requests_made) or raises."""
    params = {"limit": PAGE_LIMIT}
    if cursor:
        params["cursor"] = cursor

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = session.get(url, params=params, headers={"X-Api-Key": key}, timeout=30)
            requests_made += 1
        except requests.RequestException as e:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(f"Connection error after {MAX_ATTEMPTS} attempts: {e}")
            time.sleep(min(2 ** attempt, 10))
            continue

        if resp.status_code == 200:
            return resp.json(), requests_made

        if resp.status_code == 401:
            raise RuntimeError("Supplier API rejected the API key (401).")

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 1))
            time.sleep(retry_after)
            continue  # same attempt number — 429 doesn't count

        if resp.status_code in (500, 502, 503):
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(f"Supplier returned {resp.status_code} after {MAX_ATTEMPTS} attempts.")
            time.sleep(min(2 ** attempt, 10))
            continue

        raise RuntimeError(f"Unexpected status {resp.status_code} from supplier.")

    raise RuntimeError(f"Exhausted {MAX_ATTEMPTS} attempts.")


class SupplierSyncView(APIView):
    """POST /api/sync/supplier/"""

    def post(self, request):
        supplier_url = settings.SUPPLIER_API_URL.rstrip("/") + "/v1/products"
        supplier_key = settings.SUPPLIER_API_KEY

        session = requests.Session()
        cursor = None
        pages_fetched = 0
        requests_made = 0
        all_items = []
        rejected = []

        try:
            while True:
                data, requests_made = _fetch_page(
                    session, supplier_url, supplier_key, cursor, requests_made
                )
                pages_fetched += 1
                for item in data.get("items", []):
                    reason = _validate_item(item)
                    if reason:
                        rejected.append({
                            "supplier_sku": item.get("supplier_sku", ""),
                            "reason": reason,
                        })
                    else:
                        all_items.append(item)

                cursor = data.get("next_cursor")
                if not cursor:
                    break
        except RuntimeError as e:
            return Response(
                {"error": {"code": "SUPPLIER_UNAVAILABLE", "message": str(e), "details": []}},
                status=502,
            )

        # Deduplicate: keep latest updated_at per sku
        best = {}
        for item in all_items:
            sku = item["sku"].strip()
            updated_at_str = item.get("updated_at", "")
            try:
                updated_at = datetime.fromisoformat(
                    updated_at_str.replace("Z", "+00:00")
                )
            except ValueError:
                updated_at = datetime.min.replace(tzinfo=timezone.utc)

            if sku not in best or updated_at > best[sku]["_updated_at"]:
                item["_updated_at"] = updated_at
                best[sku] = item

        # Apply to catalogue
        created = updated = unchanged = 0
        for sku, item in best.items():
            price = Decimal(str(item["price"]).strip())
            defaults = {
                "name": (item.get("name") or "").strip(),
                "category": (item.get("category") or "").strip(),
                "brand": (item.get("brand") or "").strip(),
                "vehicle_fitment": (item.get("vehicle_fitment") or "").strip(),
                "description": (item.get("description") or "").strip(),
                "price": price,
            }
            try:
                existing = Product.objects.get(sku=sku)
                changed = any(
                    str(getattr(existing, field)) != str(val)
                    for field, val in defaults.items()
                    if field != "price"
                )
                changed = changed or existing.price != price
                if changed:
                    for field, val in defaults.items():
                        setattr(existing, field, val)
                    existing.save(update_fields=list(defaults.keys()))
                    updated += 1
                else:
                    unchanged += 1
            except Product.DoesNotExist:
                Product.objects.create(sku=sku, stock=0, **defaults)
                created += 1

        return Response({
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "rejected": rejected,
            "pages_fetched": pages_fetched,
            "requests_made": requests_made,
        })
