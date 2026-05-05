from . import views
from django.urls import path

urlpatterns = [
    path("products/", views.product_list, name="product-list"),
    path("products/<int:pk>/", views.product_detail, name="product-detail"),
    path("categories/", views.category_list, name="category-list"),
    path("categories/<int:pk>/", views.category_detail, name="category-detail"),
    path("categories/<int:category_id>/products/", views.product_by_category, name="product-by-category"),
    path("categories/<int:category_id>/products/<int:product_id>/add/", views.add_product_to_category, name="add-product-to-category"),
    path("categories/<int:category_id>/products/<int:product_id>/remove/", views.remove_product_from_category, name="remove-product-from-category"),

    # Post Routes 
    path("products/create/", views.product_create, name="create-product"),
    path("categories/create/", views.category_create, name="create-category"),

    # Put Routes
    path("products/<int:pk>/update/", views.product_update, name="update-product"),
    path("categories/<int:pk>/update/", views.category_update, name="update-category"),

    # Delete Routes
    path("products/<int:pk>/delete/", views.product_delete, name="delete-product"),
    path("categories/<int:pk>/delete/", views.category_delete, name="delete-category"),
]

