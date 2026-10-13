from django.urls import path
from .views import ForecastView, ReorderSuggestionsView
from .sync_views import SupplierSyncView

urlpatterns = [
    path("forecast/<str:sku>/", ForecastView.as_view()),
    path("reorder-suggestions/", ReorderSuggestionsView.as_view()),
    path("sync/supplier/", SupplierSyncView.as_view()),
]
