from django.db.models import QuerySet

from shop.infrastructure.models import OrderModel


class OrderQueryRepo:
    def active_orders(self) -> QuerySet:
        return OrderModel.objects.filter(status="active")

    def count_active(self) -> int:
        return OrderModel.objects.filter(status="active").count()
