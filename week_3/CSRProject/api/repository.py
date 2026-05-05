from .models import Product

class ProductRepository:
    def create_product(self, name, description, price, stock) -> Product:
        product = Product(name=name, description=description, price=price, stock=stock)
        product.save()
        return product
    
    def get_product_by_id(self, product_id) -> Product:
        return Product.objects(id=product_id).first()
    
    def update_product(self, product_id, **kwargs) -> Product:
        product = Product.objects(id=product_id).first()
        if not product:
            return None
        for key, value in kwargs.items():
            setattr(product, key, value)
        product.save()
        return product
    
    def delete_product(self, product_id) -> bool:
        product = Product.objects(id=product_id).first()
        if not product:
            return False
        product.delete()
        return True
    
    def get_all(self) -> list[Product]:
        return Product.objects()