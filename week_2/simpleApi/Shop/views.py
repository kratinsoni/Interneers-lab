from rest_framework import generics
from .models import Product
from .serializers import ProductSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import APIView, api_view

@api_view(['GET'])
def ProductList(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

class ProductList(APIView):
    def get(self, request, *args, **kwargs):
        name = request.query_params.get("name", "")

        if name:
            products = Product.objects.filter(name__icontains=name)
        else:
            products = Product.objects.all()

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ProductListCreate(generics.ListCreateAPIView):
    queryset = Product.objects.all()

    serializer_class = ProductSerializer

    def delete(self, request, *args, **kwargs):
        Product.objects.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'pk'