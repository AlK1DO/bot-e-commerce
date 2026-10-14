from app.database.firebase import get_firestore
from app.database.collections import PRODUCTS_COLLECTION
from typing import List, Dict
from app.services.catalog_cache import ProductCatalogCache


class ProductRepository:

    def __init__(self):
        self.db = get_firestore()

    def get_all(self):
        """Return all products, using an in‑memory cache with TTL.

        The actual Firestore fetch is delegated to a private helper
        ``_fetch_all`` which is passed to ``ProductCatalogCache.get_products``.
        """
        return ProductCatalogCache.get_products(self._fetch_all)

    def _fetch_all(self) -> List[Dict]:
        """Fetch fresh product list from Firestore.

        This method contains the original logic that streams all documents.
        It is used by the cache layer when the TTL expires.
        """
        documents = (
            self.db
            .collection(PRODUCTS_COLLECTION)
            .stream()
        )
        products = []
        for document in documents:
            product = document.to_dict()
            product["id"] = document.id
            products.append(product)
        return products

    def get_by_id(self, product_id: str):
        document = (
            self.db
            .collection(PRODUCTS_COLLECTION)
            .document(product_id)
            .get()
        )

        if not document.exists:
            return None

        product = document.to_dict()
        product["id"] = document.id

        return product