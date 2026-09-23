from app.repositories.product_repository import ProductRepository
from app.domain.product_filters import ProductFilters


class ProductService:

    def __init__(self):
        self.repository = ProductRepository()

    def get_product(self, product_id: str):
        product = self.repository.get_by_id(product_id)

        if product is None:
            raise ValueError("Producto no encontrado.")

        return product

    def search_products(self, filters: ProductFilters):
        products = self.repository.get_all()

        results = []

        for product in products:
            if not self._matches_filters(product, filters):
                continue

            results.append(product)

        return results

    def _matches_filters(
        self,
        product: dict,
        filters: ProductFilters
    ) -> bool:

        if filters.categoria:
            categoria = str(
                product.get("categoria", "")
            ).lower()

            if filters.categoria.lower() not in categoria:
                return False

        if filters.marca:
            marca = str(
                product.get("marca", "")
            ).lower()

            if filters.marca.lower() not in marca:
                return False

        precio = self._parse_price(
            product.get("precio")
        )

        if filters.precio_min is not None:
            if precio is None or precio < filters.precio_min:
                return False

        if filters.precio_max is not None:
            if precio is None or precio > filters.precio_max:
                return False

        if filters.solo_stock:
            stock = self._parse_stock(
                product.get("stock")
            )

            if stock <= 0:
                return False

        if filters.texto:
            search_text = filters.texto.lower().strip()

            primary_content = " ".join([
                str(product.get("titulo", "")),
                str(product.get("marca", "")),
                str(product.get("modelo", "")),
                str(product.get("categoria", "")),
                str(product.get("tarjeta_de_video", "")),
                str(product.get("graficos", "")),
                str(product.get("memoria_ram", "")),
                str(product.get("procesador", ""))
            ]).lower()

            if search_text not in primary_content:
                return False

        return True

    def _parse_price(self, value):
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        try:
            cleaned = (
                str(value)
                .replace("S/", "")
                .replace(",", "")
                .strip()
            )

            return float(cleaned)

        except ValueError:
            return None

    def _parse_stock(self, value):
        if value is None:
            return 0

        if isinstance(value, int):
            return value

        try:
            return int(value)

        except (ValueError, TypeError):
            return 0