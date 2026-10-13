"""Views for §4 Products, §5 Inventory, §6 Dealers."""
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Dealer, Product
from .serializers import (
    DealerCreateSerializer,
    DealerSerializer,
    ProductCreateSerializer,
    ProductPatchSerializer,
    ProductSerializer,
)


# ── Error helpers ─────────────────────────────────────────────────────────────

def err(code, message, details=None, http_status=400):
    return Response(
        {"error": {"code": code, "message": message, "details": details or []}},
        status=http_status,
    )


def paginate(qs, request, serializer_class):
    """Simple paginator returning {count, next, previous, results}."""
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
    items = qs[offset: offset + page_size]

    base_url = request.build_absolute_uri(request.path)
    params = request.query_params.copy()

    def make_url(p):
        params["page"] = p
        params["page_size"] = page_size
        return base_url + "?" + params.urlencode()

    return Response(
        {
            "count": total,
            "next": make_url(page + 1) if offset + page_size < total else None,
            "previous": make_url(page - 1) if page > 1 else None,
            "results": serializer_class(items, many=True).data,
        }
    )


# ── Products ──────────────────────────────────────────────────────────────────

class ProductListCreateView(APIView):
    """GET /api/products/  POST /api/products/"""

    def get(self, request):
        qs = Product.objects.all()
        search = request.query_params.get("search", "").strip()
        category = request.query_params.get("category", "").strip()
        vehicle = request.query_params.get("vehicle", "").strip()

        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(sku__icontains=search)
                | Q(name__icontains=search)
                | Q(brand__icontains=search)
            )
        if category:
            qs = qs.filter(category__iexact=category)
        if vehicle:
            qs = qs.filter(vehicle_fitment__icontains=vehicle)

        return paginate(qs, request, ProductSerializer)

    def post(self, request):
        ser = ProductCreateSerializer(data=request.data)
        if not ser.is_valid():
            return err("VALIDATION_ERROR", str(ser.errors))
        try:
            product = ser.save()
        except IntegrityError:
            return err("DUPLICATE", f"SKU {ser.validated_data['sku']} already exists.", http_status=409)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    """GET /api/products/{sku}/  PATCH /api/products/{sku}/"""

    def _get_product(self, sku):
        try:
            return Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            return None

    def get(self, request, sku):
        product = self._get_product(sku)
        if not product:
            return err("NOT_FOUND", f"Product {sku} not found.", http_status=404)
        return Response(ProductSerializer(product).data)

    def patch(self, request, sku):
        product = self._get_product(sku)
        if not product:
            return err("NOT_FOUND", f"Product {sku} not found.", http_status=404)
        ser = ProductPatchSerializer(data=request.data, partial=True)
        if not ser.is_valid():
            return err("VALIDATION_ERROR", str(ser.errors))
        product = ser.update(product, ser.validated_data)
        return Response(ProductSerializer(product).data)


# ── Inventory ─────────────────────────────────────────────────────────────────

class InventoryView(APIView):
    """PUT /api/inventory/{sku}/"""

    def put(self, request, sku):
        try:
            product = Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            return err("NOT_FOUND", f"Product {sku} not found.", http_status=404)

        quantity = request.data.get("quantity")
        if quantity is None or not isinstance(quantity, int) or quantity < 0:
            return err("VALIDATION_ERROR", "quantity must be a non-negative integer.")

        product.stock = quantity
        product.save(update_fields=["stock"])
        return Response({"sku": sku, "quantity": quantity})


# ── Dealers ───────────────────────────────────────────────────────────────────

class DealerListCreateView(APIView):
    """GET /api/dealers/  POST /api/dealers/"""

    def get(self, request):
        qs = Dealer.objects.all()
        return paginate(qs, request, DealerSerializer)

    def post(self, request):
        ser = DealerCreateSerializer(data=request.data)
        if not ser.is_valid():
            return err("VALIDATION_ERROR", str(ser.errors))
        try:
            dealer = ser.save()
        except IntegrityError:
            return err(
                "DUPLICATE",
                f"Dealer code {ser.validated_data['dealer_code']} already exists.",
                http_status=409,
            )
        return Response(DealerSerializer(dealer).data, status=status.HTTP_201_CREATED)


class DealerDetailView(APIView):
    """GET /api/dealers/{id}/"""

    def get(self, request, pk):
        try:
            dealer = Dealer.objects.get(pk=pk)
        except Dealer.DoesNotExist:
            return err("NOT_FOUND", f"Dealer {pk} not found.", http_status=404)
        return Response(DealerSerializer(dealer).data)
