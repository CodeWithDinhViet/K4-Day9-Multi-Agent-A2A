"""Order, item, seller, product, and category analysis."""

from typing import Iterable, List, TypeVar

from ..data_repository import OlistRepository
from ..models import OrderProductAnalysis


T = TypeVar("T")


def stable_unique(values: Iterable[T]) -> List[T]:
    return list(dict.fromkeys(values))


class OrderProductAgent:
    def __init__(self, repository: OlistRepository) -> None:
        self.repository = repository

    def investigate(self, order_id: str) -> OrderProductAnalysis:
        order = self.repository.get_order(order_id)
        if order is None:
            raise ValueError(f"Order {order_id!r} was not found")

        items = self.repository.get_order_items(order_id)
        item_ids = [f"{order_id}:{row['order_item_id']}" for row in items]
        seller_ids = stable_unique(row["seller_id"] for row in items)
        product_ids = stable_unique(row["product_id"] for row in items)

        categories = []
        for product_id in product_ids:
            product = self.repository.get_product(product_id)
            if product is not None and product["product_category_name"]:
                categories.append(product["product_category_name"])
        category_names = stable_unique(categories)

        return OrderProductAnalysis(
            order=order,
            item_rows=items,
            item_ids=item_ids[:5],
            seller_ids=seller_ids[:3],
            product_ids=product_ids[:5],
            category_names=category_names[:5],
            multi_item_order=len(items) >= 2,
            multi_seller_order=len(seller_ids) >= 2,
            multiple_categories=len(category_names) >= 2,
        )

