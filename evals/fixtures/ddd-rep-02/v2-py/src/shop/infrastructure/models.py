from django.db import models


class OrderModel(models.Model):
    status = models.CharField(max_length=20)
