from app.database.firebase import get_firestore
from app.database.collections import PRODUCTS_COLLECTION


class ProductRepository:

    def __init__(self):
        self.db = get_firestore()

    def get_all(self):
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