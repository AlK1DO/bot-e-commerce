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
    BUILD_PC = "armar_pc"       # Redirige a la sección "Arma tu PC" de Eagle Gaming
    HUMAN_SUPPORT = "asesor_humano"  # Deriva al asesor humano / WhatsApp
    UNKNOWN = "desconocida"
