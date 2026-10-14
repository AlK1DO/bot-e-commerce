"""Clasificación inicial por reglas; no consulta catálogo ni proveedores de IA."""

import re

from app.domain.intents import Intent
from app.domain.search_normalizer import normalize_search


class IntentService:
    OUT_OF_SCOPE_TERMS = {
        "restaurante", "receta", "clima", "politica", "eleccion", "elecciones",
        "casa", "vivienda", "hotel", "viaje", "medicina", "enfermedad",
        "tarea", "revolucion", "futbol", "partido",
    }

    def is_out_of_scope(self, message: str) -> bool:
        return bool(self.OUT_OF_SCOPE_TERMS & set(normalize_search(message).split()))

    def extract_product_query(self, message: str) -> str:
        """Retira frases de consulta; conserva marca, modelo y términos técnicos."""
        text = normalize_search(message)
        text = re.sub(r"\b(?:cuanto cuesta|cuanto vale|que precio tiene|que garantia tiene|que caracteristicas tiene|que especificaciones tiene)\b", " ", text)
        stopwords = {
            "hola", "por", "favor", "quiero", "quisiera", "saber", "el", "la",
            "los", "las", "un", "una", "de", "del", "para", "me", "puedes",
            "dime", "dices", "decir", "podrias", "podria",
            "necesito", "necesitamos", "necesitar", "venden", "vende", "vendan",
            "mostrar", "muestra", "busco", "buscar", "buscando", "comprar",
            "precio", "precios", "cuesta", "cuanto", "vale", "costo", "tiene",
            "tiene", "tienen", "tienes", "hay", "stock", "disponible", "disponibilidad", "en",
            "garantia", "caracteristicas", "especificaciones", "que", "es",
            "esta", "este", "producto", "ver",
            "juego", "juegos", "jugar", "gaming", "gamer",
        }
        return " ".join(word for word in text.split() if word not in stopwords)

    # Una intención principal por mensaje. El orden resuelve consultas mixtas.
    RULES = (
        (Intent.COMMERCIAL_INFO, r"\b(envio\w*|despacho\w*|delivery|recojo\w*|retiro|horario\w*|ubicacion\w*|direccion\w*|sector|paqueteria\w*|courier|dni|mercado libre|olva|flex)\b"),
        (Intent.COMPARISON, r"\b(compara\w*|diferencia\w*|vs|versus)\b|\bcual es mejor\b|\bque me conviene mas\b"),
        (Intent.WARRANTY, r"\b(garantia|garantias)\b"),
        (Intent.RECOMMENDATION, r"\b(recomienda\w*|recomendacion\w*|aconseja\w*|presupuesto)\b|\bcual me conviene\b"),
        (Intent.PRICE, r"\b(precio\w*|cuesta\w*|cuanto vale\w*|costo\w*)\b"),
        (Intent.AVAILABILITY, r"\b(stock|disponib\w*|agotad\w*|tienen|hay|queda\w*)\b"),
        (Intent.FEATURES, r"\b(caracteristica\w*|especificacion\w*)\b|\b(que|cuanta|cuanto)\b.*\b(ram|memoria|procesador|pantalla|almacenamiento|graficos)\b|\b(que tiene|que trae)\b"),
        (Intent.PRODUCT_SEARCH, r"\b(busco|buscar|buscando|muestra\w*|ver|comprar|laptop\w*|monitor\w*|teclado\w*|mouse|raton|procesador\w*|memoria\w*|ssd|hdd|rtx|gtx|pc|periferico\w*|componente\w*|accesorio\w*|i[3579]|\d+(?:gb|tb|hz)|\d{4})\b"),
    )

    def detect_intent(self, message: str) -> Intent:
        text = normalize_search(message)
        for intent, pattern in self.RULES:
            if re.search(pattern, text):
                return intent
        if re.fullmatch(
            r"(?:hola|buenas|buenos dias|buenas tardes|buenas noches)"
            r"(?:\s+(?:eli|eagle|asistente|amiga|amigo|que tal|como estas))?",
            text,
        ):
            return Intent.GREETING
        return Intent.UNKNOWN
