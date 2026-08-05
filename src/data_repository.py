"""Read-only access layer for the Olist CSV files.

Rows are retained in source order so later output arrays are deterministic.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional

from .config import DATA_DIR
from .models import CaseInput


Row = Dict[str, str]


def _read_csv(path: Path) -> List[Row]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _group(rows: Iterable[Row], key: str) -> Dict[str, List[Row]]:
    grouped: DefaultDict[str, List[Row]] = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return dict(grouped)


class OlistRepository:
    """Loads the dataset once and exposes explicit domain queries."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.customers = _read_csv(data_dir / "olist_customers_dataset.csv")
        self.orders = _read_csv(data_dir / "olist_orders_dataset.csv")
        self.items = _read_csv(data_dir / "olist_order_items_dataset.csv")
        self.payments = _read_csv(data_dir / "olist_order_payments_dataset.csv")
        self.reviews = _read_csv(data_dir / "olist_order_reviews_dataset.csv")
        self.products = _read_csv(data_dir / "olist_products_dataset.csv")
        self.sellers = _read_csv(data_dir / "olist_sellers_dataset.csv")
        self.geolocation = _read_csv(data_dir / "olist_geolocation_dataset.csv")
        self.category_translations = _read_csv(
            data_dir / "product_category_name_translation.csv"
        )

        self._orders_by_id = {row["order_id"]: row for row in self.orders}
        self._customers_by_id = {
            row["customer_id"]: row for row in self.customers
        }
        self._items_by_order = _group(self.items, "order_id")
        self._payments_by_order = _group(self.payments, "order_id")
        self._reviews_by_order = _group(self.reviews, "order_id")
        self._products_by_id = {
            row["product_id"]: row for row in self.products
        }
        self._sellers_by_id = {row["seller_id"]: row for row in self.sellers}
        self._orders_by_customer_id = _group(self.orders, "customer_id")

        customer_ids_by_unique: DefaultDict[str, List[str]] = defaultdict(list)
        for customer in self.customers:
            customer_ids_by_unique[customer["customer_unique_id"]].append(
                customer["customer_id"]
            )
        self._customer_ids_by_unique = dict(customer_ids_by_unique)

    def get_order(self, order_id: str) -> Optional[Row]:
        return self._orders_by_id.get(order_id)

    def get_customer(self, customer_id: str) -> Optional[Row]:
        return self._customers_by_id.get(customer_id)

    def get_order_items(self, order_id: str) -> List[Row]:
        return list(self._items_by_order.get(order_id, []))

    def get_order_payments(self, order_id: str) -> List[Row]:
        return list(self._payments_by_order.get(order_id, []))

    def get_order_reviews(self, order_id: str) -> List[Row]:
        return list(self._reviews_by_order.get(order_id, []))

    def get_product(self, product_id: str) -> Optional[Row]:
        return self._products_by_id.get(product_id)

    def get_seller(self, seller_id: str) -> Optional[Row]:
        return self._sellers_by_id.get(seller_id)

    def get_customer_history(self, customer_unique_id: str) -> List[Row]:
        history: List[Row] = []
        for customer_id in self._customer_ids_by_unique.get(customer_unique_id, []):
            history.extend(self._orders_by_customer_id.get(customer_id, []))
        return history


def load_case(path: Path) -> CaseInput:
    with path.open("r", encoding="utf-8") as handle:
        return CaseInput.from_dict(json.load(handle))

