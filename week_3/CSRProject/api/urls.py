# api/urls.py
from django.urls import path
from .views import ProductController

urlpatterns = [
    path("products/", ProductController.as_view(), name="product-list-create"),
    path(
        "products/<str:product_id>/", ProductController.as_view(), name="product-detail"
    ),
]
