from django.urls import path
from .views import (
    OrderCancelView,
    OrderConfirmView,
    OrderDeliverView,
    OrderDetailView,
    OrderDispatchView,
    OrderListCreateView,
)

urlpatterns = [
    path("orders/", OrderListCreateView.as_view()),
    path("orders/<str:order_number>/", OrderDetailView.as_view()),
    path("orders/<str:order_number>/confirm/", OrderConfirmView.as_view()),
    path("orders/<str:order_number>/dispatch/", OrderDispatchView.as_view()),
    path("orders/<str:order_number>/deliver/", OrderDeliverView.as_view()),
    path("orders/<str:order_number>/cancel/", OrderCancelView.as_view()),
]
