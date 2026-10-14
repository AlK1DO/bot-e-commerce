"""Normalización y búsqueda técnica sin dependencias de infraestructura."""

from difflib import get_close_matches
import re
import unicodedata


COMMON_TERMS = (
    "accesorio", "almacenamiento", "armada", "armadas", "categoria",
    "caracteristicas", "completa", "computadora", "disponibilidad", "envio",
    "garantia", "graficos", "horario", "juego", "juegos", "laptop",
    "memoria", "monitor", "mouse", "pago", "pantalla", "paqueteria",
    "periferico", "precio", "procesador", "provincia", "recojo", "ram",
    "stock", "tarjeta", "teclado", "tiene", "tienen", "tienes", "ubicacion",
    "video", "fuente", "gabinete", "auricular", "audifono",
)


def _correct_common_typo(word: str) -> str:
    """Corrige solo palabras comerciales conocidas; no altera modelos ni números."""
    if len(word) < 4 or word in COMMON_TERMS or any(char.isdigit() for char in word):
        return word
    matches = get_close_matches(word, COMMON_TERMS, n=1, cutoff=0.82)
    return matches[0] if matches else word


def normalize_search(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = " ".join(_correct_common_typo(word) for word in re.findall(r"[a-z0-9]+", text))
    text = re.sub(
        r"\b(?:pcs?|computadoras?|computadores?|ordenadores?)\s+"
        r"(?:armad[oa]s?|complet[oa]s?|ensamblad[oa]s?|de\s+escritorio)\b",
        "pc completa", text,
    )
    text = re.sub(r"\b(?:intel\s+)?(?:core\s+)?(i[3579])\b", r"\1", text)
    text = re.sub(r"\b(?:amd\s+)?(?:ryzen\s+)?(r[3579]|ryzen\s*[3579])\b", r"ryzen", text)
    text = re.sub(r"\b(\d+)\s*(?:gb\s*)?(?:de\s+)?ram\b", r"\1gb", text)
    text = re.sub(r"\bram\s+(\d+)\s*(?:gb\b)?", r"\1gb", text)
    text = re.sub(r"\b(\d+)\s+(gb|tb|hz)\b", r"\1\2", text)
    text = re.sub(r"\b(rtx|gtx)\s*(\d{3,4})\b", r"\1 \2", text)
    text = re.sub(r"\brx\s*(\d{4})\b", r"rx \1", text)
    text = re.sub(r"\blaptops?\b", "laptop", text)
    text = re.sub(r"\bmonitores\b", "monitor", text)
    text = re.sub(r"\bprocesadores\b", "procesador", text)
    text = re.sub(r"\bteclados\b", "teclado", text)
    text = re.sub(r"\bmouses?\b|\bratones?\b", "mouse", text)
    text = re.sub(r"\baudifonos?\b|\bauriculares?\b|\bheadsets?\b", "audifono", text)
    text = re.sub(r"\bperifericos\b", "periferico", text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _fields_for(term: str) -> tuple[str, ...]:
    if re.fullmatch(r"(?:rtx|gtx|rx)(?: \d{3,4})?|\d{4}", term):
        return ("tarjeta_de_video", "graficos", "titulo")
    if re.fullmatch(r"i[3579]|ryzen", term):
        return ("procesador", "titulo")
    if re.fullmatch(r"\d+gb", term):
        return ("memoria_ram", "titulo")
    if re.fullmatch(r"\d+tb", term) or term in {"ssd", "hdd", "nvme"}:
        return ("almacenamiento", "titulo")
    if re.fullmatch(r"\d+hz", term):
        return ("pantalla", "titulo")
    if term in {"laptop", "monitor", "teclado", "mouse", "audifono", "procesador"}:
        return ("categoria", "titulo")
    return ("titulo", "marca", "modelo", "categoria")


def matches_search(product: dict, query: str) -> bool:
    """Exige todos los términos; nunca consulta descripciones comerciales."""
    terms = re.findall(r"pc completa|(?:rtx|gtx|rx) \d{3,4}|[a-z0-9]+", normalize_search(query))
    for term in terms:
        if term == "pc completa":
            category = normalize_search(product.get("categoria"))
            title = normalize_search(product.get("titulo"))
            if category != "pc completa" and not re.match(
                r"^(?:pc completa\b|computadora\b|computador\b|ordenador\b|pc\s+(?:gamer|gaming)\b)", title
            ):
                return False
            continue
        pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
        if not any(
            re.search(pattern, normalize_search(product.get(field)))
            for field in _fields_for(term)
            if product.get(field) is not None
        ):
            return False
    return True
