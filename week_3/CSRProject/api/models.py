from datetime import datetime

from mongoengine import DateTimeField, Document, StringField, FloatField, IntField

# Create your models here.


class Product(Document):
    name = StringField(required=True)
    description = StringField()
    price = FloatField(required=True)
    stock = IntField(required=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {"collection": "products"}

    def save(self, *args, **kwargs):
        # If the document is brand new, ensure created_at is set
        if not self.created_at:
            self.created_at = datetime.datetime.utcnow()

        # Always update the updated_at field before saving
        self.updated_at = datetime.datetime.utcnow()

        # Call the original save method to actually write to the database
        return super(Product, self).save(*args, **kwargs)
