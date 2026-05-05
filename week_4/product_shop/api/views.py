from django.shortcuts import render
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# Product List API View

@api_view(["GET"])
def product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response({"message": "Products Fetched Successfully", "data": serializer.data}, status=status.HTTP_200_OK)

@api_view(["GET"])
def product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"message": "Product Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ProductSerializer(product)
    return Response({"message": "Product Fetched Successfully", "data": serializer.data}, status=status.HTTP_200_OK)

@api_view(["POST"])
def product_create(request):
    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Product Created Successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
    return Response({"message": "Product Creation Failed", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["PUT"])
def product_update(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"message": "Product Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ProductSerializer(product, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Product Updated Successfully", "data": serializer.data}, status=status.HTTP_200_OK)
    return Response({"message": "Product Update Failed", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
def product_delete(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"message": "Product Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    product.delete()
    return Response({"message": "Product Deleted Successfully"}, status=status.HTTP_204_NO_CONTENT)

@api_view(["GET"])
def product_by_category(request, category_id):
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return Response({"message": "Category Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    products = category.products.all()
    serializer = ProductSerializer(products, many=True)
    return Response({"message": "Products Fetched Successfully", "data": serializer.data}, status=status.HTTP_200_OK)

@api_view(["POST"])
def add_product_to_category(request, category_id, product_id):
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return Response({"message": "Category Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return Response({"message": "Product Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    category.products.add(product)
    return Response({"message": "Product Added to Category Successfully"}, status=status.HTTP_200_OK)   

@api_view(["POST"])
def remove_product_from_category(request, category_id, product_id):
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return Response({"message": "Category Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return Response({"message": "Product Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    category.products.remove(product)
    return Response({"message": "Product Removed from Category Successfully"}, status=status.HTTP_200_OK)

# Category List API View

@api_view(["GET"])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response({"message": "Categories Fetched Successfully", "data": serializer.data}, status=status.HTTP_200_OK)

@api_view(["GET"])
def category_detail(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return Response({"message": "Category Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = CategorySerializer(category)
    return Response({"message": "Category Fetched Successfully", "data": serializer.data}, status=status.HTTP_200_OK)

@api_view(["POST"])
def category_create(request):
    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Category Created Successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
    return Response({"message": "Category Creation Failed", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["PUT"])
def category_update(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return Response({"message": "Category Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = CategorySerializer(category, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Category Updated Successfully", "data": serializer.data}, status=status.HTTP_200_OK)
    return Response({"message": "Category Update Failed", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
def category_delete(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return Response({"message": "Category Not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    category.delete()
    return Response({"message": "Category Deleted Successfully"}, status=status.HTTP_204_NO_CONTENT)
