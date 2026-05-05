# django_app/models.py

from django.db import models


class UserModel(models.Model):
    name = models.CharField(max_length=100)
