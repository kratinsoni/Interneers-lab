# api/views.py
import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .service import ProductService


@method_decorator(csrf_exempt, name="dispatch")
class ProductController(View):
    service = ProductService()

    def get(self, request, product_id=None):
        if product_id:
            product = self.service.get_product_by_id(product_id)
            if product:
                return JsonResponse(product, status=200)
            return JsonResponse({"error": "Product not found"}, status=404)

        products = self.service.get_all_products()
        return JsonResponse(products, safe=False, status=200)

    def post(self, request):
        try:
            data = json.loads(request.body)
            product = self.service.create_product(**data)
            return JsonResponse(product, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def put(self, request, product_id):
        try:
            data = json.loads(request.body)
            product = self.service.update_product(product_id, **data)
            if product:
                return JsonResponse(product, status=200)
            return JsonResponse({"error": "Product not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, product_id):
        success = self.service.delete_product(product_id)
        if success:
            return JsonResponse({"message": "Product deleted successfully"}, status=204)
        return JsonResponse({"error": "Product not found"}, status=404)
