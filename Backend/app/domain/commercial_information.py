"""Información comercial revisada fuera del catálogo de productos.

Los datos marcados como pendientes no se muestran como políticas definitivas.
Actualiza este archivo cuando la tienda confirme el dato operativo.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.search_normalizer import normalize_search


class CommercialTopic(StrEnum):
    SHIPPING = "envios"
    PICKUP = "recojo"
    SCHEDULE = "horarios"
    LOCATION = "ubicaciones"
    PAYMENT = "pagos"
    DELIVERY_DATA = "datos_para_envio"


@dataclass(frozen=True)
class CommercialAnswer:
    topic: CommercialTopic
    message: str
    resolved: bool


def detect_commercial_topic(message: str) -> CommercialTopic | None:
    text = normalize_search(message)
    if any(term in text for term in ("horario", "hora", "abren", "cierran")):
        return CommercialTopic.SCHEDULE
    if any(term in text for term in ("donde", "ubicacion", "direccion", "sector", "tienda")):
        return CommercialTopic.LOCATION
    if any(term in text for term in ("recojo", "recoger", "recojer", "retiro presencial")):
        return CommercialTopic.PICKUP
    if any(term in text for term in ("pago", "paga", "pagar", "cuotas", "deposito", "transferencia")):
        return CommercialTopic.PAYMENT
    if any(term in text for term in ("dni", "datos", "paqueteria", "courier", "currier", "sede")):
        return CommercialTopic.DELIVERY_DATA
    if any(term in text for term in ("envio", "envios", "despacho", "delivery", "olva", "provincia", "mercado libre", "flex")):
        return CommercialTopic.SHIPPING
    return None


COMMERCIAL_ANSWERS = {
    CommercialTopic.SHIPPING: CommercialAnswer(
        CommercialTopic.SHIPPING,
        "Realizamos envíos a Lima y provincia. Para provincia, puedes indicar la empresa de paquetería de tu preferencia y la sede de destino. La gestión del envío se realiza en un plazo de hasta 24 horas hábiles antes del despacho. Por Mercado Libre contamos con Olva de 11:00 a. m. a 7:00 p. m. y Flex, que recoge el pedido.",
        True,
    ),
    CommercialTopic.PICKUP: CommercialAnswer(
        CommercialTopic.PICKUP,
        "Puedes coordinar recojo presencial en la tienda de Cyber Plaza. También se realizan envíos desde allí de 10:00 a. m. a 7:00 p. m. Indícanos el producto para confirmar su disponibilidad antes de acercarte.",
        True,
    ),
    CommercialTopic.SCHEDULE: CommercialAnswer(
        CommercialTopic.SCHEDULE,
        "Horario registrado: Ripley atiende de 11:00 a. m. a 8:00 p. m. La tienda de Cyber Plaza atiende recojos y envíos de 10:00 a. m. a 7:00 p. m. Saga Falabella e Intercorp tienen atención presencial; su horario específico requiere confirmación.",
        False,
    ),
    CommercialTopic.LOCATION: CommercialAnswer(
        CommercialTopic.LOCATION,
        "Tenemos puntos de atención registrados en Sector A y Sector B, además de la tienda de Cyber Plaza. Para darte la ubicación exacta o confirmar qué punto corresponde a Saga Falabella, Intercorp o Ripley, necesitamos validarlo con la tienda.",
        False,
    ),
    CommercialTopic.PAYMENT: CommercialAnswer(
        CommercialTopic.PAYMENT,
        "Las condiciones de pago necesitan confirmación antes de informarlas como definitivas. Completa tu pedido desde tu sesión para recibir la indicación correcta antes de que se prepare el producto.",
        False,
    ),
    CommercialTopic.DELIVERY_DATA: CommercialAnswer(
        CommercialTopic.DELIVERY_DATA,
        "Para coordinar un envío se requieren los datos completos del comprador, DNI, empresa de paquetería preferida y, si el destino es provincia, la sede de entrega. Completa estos datos desde tu sesión o checkout seguro; no compartas tu DNI por este chat.",
        True,
    ),
}
