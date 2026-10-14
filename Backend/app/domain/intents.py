from enum import StrEnum


class Intent(StrEnum):
    GREETING = "saludo"
    PRICE = "precio"
    AVAILABILITY = "disponibilidad"
    FEATURES = "caracteristicas"
    WARRANTY = "garantia"
    COMMERCIAL_INFO = "informacion_comercial"
    RECOMMENDATION = "recomendacion"
    COMPARISON = "comparacion"
    PRODUCT_SEARCH = "buscar_producto"
    UNKNOWN = "desconocida"
