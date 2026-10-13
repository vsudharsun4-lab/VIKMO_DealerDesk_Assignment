"""Order business logic — §7."""
import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from products.models import Product
from .models import DailyOrderCounter, Order, OrderItem

TAX_RATE = Decimal("0.18")
TWO_DP = Decimal("0.01")


def _round_half_up(d: Decimal) -> Decimal:
    return d.quantize(TWO_DP, rounding=ROUND_HALF_UP)


def _compute_lines(items_data, use_locked_price=False, existing_items=None):
    """
    Compute line amounts.
    items_data: list of {"sku": ..., "quantity": ...}
    Returns list of dicts with all money fields, plus aggregate totals.
    """
    lines = []
    subtotal = Decimal("0")
    tax_total = Decimal("0")

    price_map = {}
    if not use_locked_price:
        skus = [i["sku"] for i in items_data]
        for p in Product.objects.filter(sku__in=skus):
            price_map[p.sku] = p.price
    else:
        for item in (existing_items or []):
            price_map[item.sku] = item.unit_price

    for item in items_data:
        sku = item["sku"]
        qty = item["quantity"]
        price = price_map.get(sku)
        if price is None:
            raise KeyError(sku)
        line_sub = price * qty
        line_tax = _round_half_up(line_sub * TAX_RATE)
        line_tot = line_sub + line_tax
        subtotal += line_sub
        tax_total += line_tax
        lines.append({
            "sku": sku,
            "quantity": qty,
            "unit_price": price,
            "line_subtotal": line_sub,
            "line_tax": line_tax,
            "line_total": line_tot,
        })

    grand_total = subtotal + tax_total
    return lines, subtotal, tax_total, grand_total


def _next_order_number(date):
    """Thread-safe daily sequence using SELECT FOR UPDATE."""
    try:
        with transaction.atomic():
            DailyOrderCounter.objects.create(date=date, last_seq=0)
    except IntegrityError:
        pass
    counter = DailyOrderCounter.objects.select_for_update().get(date=date)
    counter.last_seq += 1
    counter.save(update_fields=["last_seq"])
    return f"ORD-{date.strftime('%Y%m%d')}-{counter.last_seq:04d}"


def _body_hash(body: dict) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode()
    ).hexdigest()


def validate_items(items_data):
    """Validate the items list. Returns errors list or None."""
    if not items_data:
        return "At least one item is required."

    skus_seen = set()
    for item in items_data:
        sku = item.get("sku", "")
        qty = item.get("quantity")
        if not sku:
            return "Each item must have a sku."
        if sku in skus_seen:
            return f"SKU {sku} appears more than once."
        skus_seen.add(sku)
        if not isinstance(qty, int) or qty < 1:
            return f"quantity for {sku} must be an integer >= 1."

    # Check all SKUs exist
    existing = set(Product.objects.filter(sku__in=skus_seen).values_list("sku", flat=True))
    missing = skus_seen - existing
    if missing:
        return f"Unknown SKU(s): {', '.join(sorted(missing))}."

    return None


@transaction.atomic
def create_order(dealer_id, items_data, idempotency_key=None, body=None):
    """Create a DRAFT order. Returns (order, created) or raises."""
    from products.models import Dealer
    try:
        dealer = Dealer.objects.get(pk=dealer_id)
    except Dealer.DoesNotExist:
        raise ValueError(f"Dealer {dealer_id} not found.")

    body_hash = _body_hash(body or {}) if idempotency_key else None

    # Idempotency check
    if idempotency_key:
        existing = Order.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if existing.idempotency_body_hash != body_hash:
                raise ConflictError("IDEMPOTENCY_CONFLICT", "Same Idempotency-Key reused with a different request body.")
            return existing, False

    err = validate_items(items_data)
    if err:
        raise ValidationError(err)

    order_date = timezone.localdate()

    # Compute lines (DRAFT: use current product prices)
    lines, subtotal, tax_total, grand_total = _compute_lines(items_data)

    # Resolve names
    skus = [i["sku"] for i in items_data]
    name_map = {p.sku: p.name for p in Product.objects.filter(sku__in=skus)}

    order_number = _next_order_number(order_date)
    try:
        order = Order.objects.create(
            order_number=order_number,
            dealer=dealer,
            status=Order.STATUS_DRAFT,
            subtotal=subtotal,
            tax_total=tax_total,
            grand_total=grand_total,
            idempotency_key=idempotency_key or None,
            idempotency_body_hash=body_hash,
        )
    except IntegrityError:
        if idempotency_key:
            existing = Order.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                if existing.idempotency_body_hash != body_hash:
                    raise ConflictError("IDEMPOTENCY_CONFLICT", "Same Idempotency-Key reused with a different request body.")
                return existing, False
        raise

    for line in lines:
        OrderItem.objects.create(
            order=order,
            sku=line["sku"],
            name=name_map.get(line["sku"], ""),
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            line_subtotal=line["line_subtotal"],
            line_tax=line["line_tax"],
            line_total=line["line_total"],
        )
    return order, True


@transaction.atomic
def update_order_items(order, items_data):
    """Replace items of a DRAFT order."""
    if order.status != Order.STATUS_DRAFT:
        raise ConflictError("ORDER_LOCKED", "Order is not in DRAFT status.")

    err = validate_items(items_data)
    if err:
        raise ValidationError(err)

    lines, subtotal, tax_total, grand_total = _compute_lines(items_data)
    skus = [i["sku"] for i in items_data]
    name_map = {p.sku: p.name for p in Product.objects.filter(sku__in=skus)}

    order.items.all().delete()
    for line in lines:
        OrderItem.objects.create(
            order=order,
            sku=line["sku"],
            name=name_map.get(line["sku"], ""),
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            line_subtotal=line["line_subtotal"],
            line_tax=line["line_tax"],
            line_total=line["line_total"],
        )
    order.subtotal = subtotal
    order.tax_total = tax_total
    order.grand_total = grand_total
    order.save(update_fields=["subtotal", "tax_total", "grand_total", "updated_at"])
    return order


@transaction.atomic
def confirm_order(order):
    """DRAFT → CONFIRMED: all-or-nothing stock deduction."""
    if order.status != Order.STATUS_DRAFT:
        raise ConflictError("INVALID_TRANSITION", "Can only confirm a DRAFT order.")

    items = list(order.items.all())

    # Lock all affected products for update (prevents oversell)
    skus = [i.sku for i in items]
    products = {
        p.sku: p
        for p in Product.objects.select_for_update().filter(sku__in=skus)
    }

    # Check stock
    short = []
    for item in items:
        p = products.get(item.sku)
        if p and p.stock < item.quantity:
            short.append({
                "sku": item.sku,
                "requested": item.quantity,
                "available": p.stock,
            })

    if short:
        messages = ". ".join(
            f"Insufficient stock for {products[s['sku']].name}. Available: {s['available']}, Requested: {s['requested']}"
            for s in short
        )
        raise ConflictError("INSUFFICIENT_STOCK", messages, short)

    # Lock prices and deduct stock
    for item in items:
        p = products[item.sku]
        # Lock unit price to current product price at confirm time
        item.unit_price = p.price
        line_sub = item.unit_price * item.quantity
        item.line_subtotal = line_sub
        item.line_tax = _round_half_up(line_sub * TAX_RATE)
        item.line_total = item.line_subtotal + item.line_tax
        item.save(update_fields=["unit_price", "line_subtotal", "line_tax", "line_total"])
        p.stock -= item.quantity
        p.save(update_fields=["stock"])

    # Recompute order totals
    order.subtotal = sum(i.line_subtotal for i in items)
    order.tax_total = sum(i.line_tax for i in items)
    order.grand_total = order.subtotal + order.tax_total
    order.status = Order.STATUS_CONFIRMED
    order.save(update_fields=["status", "subtotal", "tax_total", "grand_total", "updated_at"])
    return order


@transaction.atomic
def dispatch_order(order):
    if order.status != Order.STATUS_CONFIRMED:
        raise ConflictError("INVALID_TRANSITION", "Can only dispatch a CONFIRMED order.")
    order.status = Order.STATUS_DISPATCHED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def deliver_order(order):
    if order.status != Order.STATUS_DISPATCHED:
        raise ConflictError("INVALID_TRANSITION", "Can only deliver a DISPATCHED order.")
    order.status = Order.STATUS_DELIVERED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def cancel_order(order):
    if order.status not in (Order.STATUS_DRAFT, Order.STATUS_CONFIRMED):
        raise ConflictError("INVALID_TRANSITION", "Only DRAFT or CONFIRMED orders can be cancelled.")

    if order.status == Order.STATUS_CONFIRMED:
        # Restore stock
        skus = [i.sku for i in order.items.all()]
        products = {
            p.sku: p
            for p in Product.objects.select_for_update().filter(sku__in=skus)
        }
        for item in order.items.all():
            p = products.get(item.sku)
            if p:
                p.stock += item.quantity
                p.save(update_fields=["stock"])

    order.status = Order.STATUS_CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


# ── Custom exceptions ─────────────────────────────────────────────────────────

class ValidationError(Exception):
    def __init__(self, message, details=None):
        self.message = message
        self.details = details or []
        super().__init__(message)


class ConflictError(Exception):
    def __init__(self, code, message, details=None):
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(message)
