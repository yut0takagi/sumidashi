from inventory.domain.warehouse import Warehouse


def close_warehouse(warehouse: Warehouse) -> None:
    warehouse.set_status("closed")
