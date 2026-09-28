import re

from app.domain.search_normalizer import normalize_search


def is_processor_request(message: str) -> bool:
    return bool(re.search(r"\b(procesador(?:es)?|cpu)\b", normalize_search(message)))


def is_processor_product(product: dict) -> bool:
    category = normalize_search(product.get('categoria'))
    title = normalize_search(product.get('titulo'))
    return category in {'procesador', 'procesadores'} or bool(
        re.match(r'^procesador\b', title)
    )


def processor_query(message: str) -> str:
    """Conserva restricciones explícitas; el uso no es un término del catálogo."""
    text = normalize_search(message)
    terms = re.findall(r'\b(?:intel|amd|ryzen|i[3579]|\d{4,5}[a-z]{0,3})\b', text)
    # Números aislados podrían ser presupuesto; solo modelos con sufijo se retienen.
    terms = [term for term in terms if not term.isdigit()]
    return ' '.join(terms)
