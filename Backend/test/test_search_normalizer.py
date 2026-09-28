import unittest

from app.domain.search_normalizer import matches_search, normalize_search


class SearchTests(unittest.TestCase):
    def test_ram_variants(self):
        for query in ("16gb", "16 gb", "16 de ram", "ram 16", "16 GB RAM"):
            with self.subTest(query=query):
                self.assertEqual(normalize_search(query), "16gb")
                self.assertTrue(matches_search({"memoria_ram": "16 GB DDR5"}, query))

    def test_requested_queries(self):
        cases = [
            ({"procesador": "Intel Core i5-12400"}, "i5"),
            ({"graficos": "NVIDIA RTX4060 8GB"}, "rtx 4060"),
            ({"graficos": "NVIDIA RTX 4060"}, "4060"),
            ({"almacenamiento": "SSD 1 TB"}, "1tb"),
            ({"categoria": "Monitores", "pantalla": "24 pulgadas 144 Hz"}, "monitor 144hz"),
            ({"categoria": "Laptops", "marca": "Lenovo"}, "laptop lenovo"),
        ]
        for product, query in cases:
            with self.subTest(query=query):
                self.assertTrue(matches_search(product, query))

    def test_no_description_or_unrelated_fields(self):
        self.assertFalse(matches_search({"titulo": "Procesador", "descripcion": "Compatible con GPUs RTX"}, "rtx"))
        self.assertFalse(matches_search({"almacenamiento": "16GB", "graficos": "16GB"}, "16gb"))
        self.assertFalse(matches_search({"descripcion": "144Hz"}, "144hz"))

    def test_exact_values_and_all_terms(self):
        for product, query in [
            ({"memoria_ram": "116GB"}, "16gb"),
            ({"almacenamiento": "11TB"}, "1tb"),
            ({"graficos": "RTX 40600"}, "rtx 4060"),
            ({"categoria": "Laptop", "marca": "Asus"}, "laptop lenovo"),
            ({"graficos": "RTX 3060 y GTX 4060"}, "rtx 4060"),
        ]:
            with self.subTest(query=query, product=product):
                self.assertFalse(matches_search(product, query))

    def test_missing_fields_and_empty_query(self):
        self.assertFalse(matches_search({"titulo": None}, "i5"))
        self.assertTrue(matches_search({}, "  "))
        self.assertTrue(matches_search({"marca": "LÉNOVO"}, "lenovo"))

    def test_common_typos(self):
        self.assertEqual(normalize_search("monitr 144hz"), "monitor 144hz")
        self.assertEqual(normalize_search("procesdor para juegs"), "procesador para juegos")
        self.assertEqual(normalize_search("tinen pc armads"), "tienen pc completa")
        self.assertEqual(normalize_search("rtx 4060"), "rtx 4060")


if __name__ == "__main__":
    unittest.main()
