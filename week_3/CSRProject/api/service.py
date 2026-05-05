from .repository import ProductRepository

class ProductService:
    def __init__(self):
        self.repository = ProductRepository()
    
    def create_product(self, name, description, price, stock):
        product = self.repository.create_product(name, description, price, stock)
        return self._serialize(product)
    
    def get_product_by_id(self, product_id):
        product = self.repository.get_product_by_id(product_id)
        return self._serialize(product) if product else None
    
    def update_product(self, product_id, **kwargs):
        product = self.repository.update_product(product_id, **kwargs)
        return self._serialize(product) if product else None
    
    def delete_product(self, product_id):
        return self.repository.delete_product(product_id)
    
    def get_all_products(self):
        return [self._serialize(product) for product in self.repository.get_all()]
    
    def _serialize(self, product):
        return {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        }