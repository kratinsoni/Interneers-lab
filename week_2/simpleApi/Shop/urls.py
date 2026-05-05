from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.ProductListCreate.as_view(), name="product-list-create"),
    path("products/<int:pk>/", views.ProductDetail.as_view(), name="product-detail"),
    path("products/search/", views.ProductList.as_view(), name="product-search"),
    path("products/function-based/", views.ProductList.as_view(), name="product-function-based"),
]
