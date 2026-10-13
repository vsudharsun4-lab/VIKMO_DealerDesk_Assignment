from django.urls import path
from .views import (
    DealerDetailView,
    DealerListCreateView,
    InventoryView,
    ProductDetailView,
    ProductListCreateView,
)

urlpatterns = [
    path("products/", ProductListCreateView.as_view()),
    path("products/<str:sku>/", ProductDetailView.as_view()),
    path("inventory/<str:sku>/", InventoryView.as_view()),
    path("dealers/", DealerListCreateView.as_view()),
    path("dealers/<int:pk>/", DealerDetailView.as_view()),
]
