"""Order views — §7."""
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Order
from .serializers import OrderSerializer
from .services import (
    ConflictError,
    ValidationError,
    cancel_order,
    confirm_order,
    create_order,
    deliver_order,
    dispatch_order,
    update_order_items,
)


def err(code, message, details=None, http_status=400):
    return Response(
        {"error": {"code": code, "message": message, "details": details or []}},
        status=http_status,
    )


def paginate_orders(qs, request):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1
    try:
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    except ValueError:
        page_size = 20

    total = qs.count()
    offset = (page - 1) * page_size
    items = qs.prefetch_related("items")[offset: offset + page_size]

    base_url = request.build_absolute_uri(request.path)
    params = request.query_params.copy()

    def make_url(p):
        params["page"] = p
        params["page_size"] = page_size
        return base_url + "?" + params.urlencode()

    return Response({
        "count": total,
        "next": make_url(page + 1) if offset + page_size < total else None,
        "previous": make_url(page - 1) if page > 1 else None,
        "results": OrderSerializer(items, many=True).data,
    })


class OrderListCreateView(APIView):
    """GET /api/orders/  POST /api/orders/"""

    def get(self, request):
        qs = Order.objects.all()
        dealer_id = request.query_params.get("dealer_id")
        status_filter = request.query_params.get("status")
        if dealer_id:
            qs = qs.filter(dealer_id=dealer_id)
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        qs = qs.order_by("-created_at")
        return paginate_orders(qs, request)

    def post(self, request):
        dealer_id = request.data.get("dealer_id")
        items_data = request.data.get("items", [])
        idempotency_key = request.headers.get("Idempotency-Key")

        if dealer_id is None:
            return err("VALIDATION_ERROR", "dealer_id is required.")

        try:
            order, created = create_order(
                dealer_id=dealer_id,
                items_data=items_data,
                idempotency_key=idempotency_key,
                body=request.data,
            )
        except ValidationError as e:
            return err("VALIDATION_ERROR", e.message, e.details)
        except ConflictError as e:
            return err(e.code, e.message, e.details, http_status=409)
        except ValueError as e:
            return err("VALIDATION_ERROR", str(e))

        order_data = OrderSerializer(order.prefetch_items() if hasattr(order, 'prefetch_items') else order).data
        # Reload with prefetch
        order = Order.objects.prefetch_related("items").get(pk=order.pk)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(OrderSerializer(order).data, status=http_status)


class OrderDetailView(APIView):
    """GET /api/orders/{order_number}/  PUT /api/orders/{order_number}/"""

    def _get_order(self, order_number):
        try:
            return Order.objects.prefetch_related("items").get(order_number=order_number)
        except Order.DoesNotExist:
            return None

    def get(self, request, order_number):
        order = self._get_order(order_number)
        if not order:
            return err("NOT_FOUND", f"Order {order_number} not found.", http_status=404)
        return Response(OrderSerializer(order).data)

    def put(self, request, order_number):
        order = self._get_order(order_number)
        if not order:
            return err("NOT_FOUND", f"Order {order_number} not found.", http_status=404)
        items_data = request.data.get("items", [])
        try:
            order = update_order_items(order, items_data)
        except ValidationError as e:
            return err("VALIDATION_ERROR", e.message, e.details)
        except ConflictError as e:
            return err(e.code, e.message, e.details, http_status=409)
        order = Order.objects.prefetch_related("items").get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderConfirmView(APIView):
    """POST /api/orders/{order_number}/confirm/"""

    def post(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return err("NOT_FOUND", f"Order {order_number} not found.", http_status=404)
        try:
            order = confirm_order(order)
        except ConflictError as e:
            return err(e.code, e.message, e.details, http_status=409)
        order = Order.objects.prefetch_related("items").get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderDispatchView(APIView):
    """POST /api/orders/{order_number}/dispatch/"""

    def post(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return err("NOT_FOUND", f"Order {order_number} not found.", http_status=404)
        try:
            order = dispatch_order(order)
        except ConflictError as e:
            return err(e.code, e.message, e.details, http_status=409)
        order = Order.objects.prefetch_related("items").get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderDeliverView(APIView):
    """POST /api/orders/{order_number}/deliver/"""

    def post(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return err("NOT_FOUND", f"Order {order_number} not found.", http_status=404)
        try:
            order = deliver_order(order)
        except ConflictError as e:
            return err(e.code, e.message, e.details, http_status=409)
        order = Order.objects.prefetch_related("items").get(pk=order.pk)
        return Response(OrderSerializer(order).data)


class OrderCancelView(APIView):
    """POST /api/orders/{order_number}/cancel/"""

    def post(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return err("NOT_FOUND", f"Order {order_number} not found.", http_status=404)
        try:
            order = cancel_order(order)
        except ConflictError as e:
            return err(e.code, e.message, e.details, http_status=409)
        order = Order.objects.prefetch_related("items").get(pk=order.pk)
        return Response(OrderSerializer(order).data)
