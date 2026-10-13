"""Forecast and reorder views — §10."""
import csv
import math
import statistics
from datetime import date
from pathlib import Path

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product

FORECAST_WEEKS = [
    "2026-09-28",
    "2026-10-05",
    "2026-10-12",
    "2026-10-19",
]

_FORECAST_DATA = None  # {sku: [{"week_start": ..., "forecast_units": ...}]}
_LEAD_TIMES = None     # {sku: int}
_SIGMA_CACHE = None    # {sku: float}


def _load_forecast():
    global _FORECAST_DATA
    if _FORECAST_DATA is not None:
        return _FORECAST_DATA
    # ml/forecast.csv is at <repo_root>/ml/forecast.csv
    forecast_path = Path(__file__).resolve().parent.parent / "ml" / "forecast.csv"
    if not forecast_path.exists():
        forecast_path = settings.BASE_DIR / "ml" / "forecast.csv"
    data = {}
    if forecast_path.exists():
        with open(forecast_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sku = row["sku"]
                data.setdefault(sku, []).append({
                    "week_start": row["week_start"],
                    "forecast_units": float(row["forecast_units"]),
                })
        # Sort each SKU's forecast by week
        for sku in data:
            data[sku].sort(key=lambda x: x["week_start"])
    _FORECAST_DATA = data
    return data


def _load_lead_times():
    global _LEAD_TIMES
    if _LEAD_TIMES is not None:
        return _LEAD_TIMES
    path = settings.DATA_DIR / "lead_times.csv"
    lt = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lt[row["sku"]] = int(row["lead_time_weeks"])
    _LEAD_TIMES = lt
    return lt


def _load_sigma():
    """Sample std dev of units_sold over last 12 weeks per SKU."""
    global _SIGMA_CACHE
    if _SIGMA_CACHE is not None:
        return _SIGMA_CACHE
    path = settings.DATA_DIR / "sales_history.csv"
    sku_history = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sku_history.setdefault(row["sku"], []).append(
                (row["week_start"], float(row["units_sold"]))
            )
    result = {}
    for sku, records in sku_history.items():
        records.sort(key=lambda x: x[0])
        recent_12 = [u for _, u in records[-12:]]
        if len(recent_12) < 2:
            result[sku] = 0.0
        else:
            result[sku] = statistics.stdev(recent_12)
    _SIGMA_CACHE = result
    return result


def err(code, message, details=None, http_status=400):
    return Response(
        {"error": {"code": code, "message": message, "details": details or []}},
        status=http_status,
    )


class ForecastView(APIView):
    """GET /api/forecast/{sku}/"""

    def get(self, request, sku):
        forecast_data = _load_forecast()
        lead_times = _load_lead_times()

        if sku not in lead_times or sku not in forecast_data:
            return err("NOT_FOUND", f"{sku} is not a forecast SKU.", http_status=404)

        return Response({
            "sku": sku,
            "forecast": forecast_data[sku],
        })


class ReorderSuggestionsView(APIView):
    """GET /api/reorder-suggestions/"""

    def get(self, request):
        forecast_data = _load_forecast()
        lead_times = _load_lead_times()
        sigma_map = _load_sigma()

        results = []
        for sku, lt in lead_times.items():
            forecast = forecast_data.get(sku, [])
            # lead_time_demand = sum of first L weeks of forecast
            lead_time_demand = sum(
                f["forecast_units"] for f in forecast[:lt]
            )
            sigma = sigma_map.get(sku, 0.0)
            safety_stock = math.ceil(1.65 * sigma * math.sqrt(lt))

            reorder_point = lead_time_demand + safety_stock

            try:
                product = Product.objects.get(sku=sku)
                current_stock = product.stock
            except Product.DoesNotExist:
                current_stock = 0

            reorder_qty = max(0, math.ceil(reorder_point - current_stock))

            results.append({
                "sku": sku,
                "current_stock": current_stock,
                "lead_time_weeks": lt,
                "lead_time_demand": round(lead_time_demand, 2),
                "safety_stock": safety_stock,
                "reorder_point": round(reorder_point, 2),
                "reorder_qty": reorder_qty,
            })

        return Response({"results": results})
