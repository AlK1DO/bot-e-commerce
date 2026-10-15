"""Servicio de asesoramiento técnico y compatibilidad de hardware para Eagle Gaming.

Resuelve dudas técnicas de clientes sobre compatibilidad de sockets, placas madre,
memorias RAM, paneles de monitor, fuentes de poder y recomendaciones por uso (programación,
gaming, diseño, streaming), tanto como motor autónomo como respaldo cuando la IA no responde.
"""

import re
from typing import List, Tuple
from app.domain.search_normalizer import normalize_search


class HardwareAdvisorService:

    @staticmethod
    def is_technical_or_hardware_query(message: str) -> bool:
        """Determina si el mensaje contiene dudas de compatibilidad o términos de hardware."""
        text = normalize_search(message)
        patterns = [
            # Placas y chipsets
            r"\b(placa\w*|motherboard|tarjeta\s+madre|socket|chipset)\b",
            r"\b(b660|h610|b760|z690|z790|lga\s*1700|am4|b450|b550|a520|x570|am5|b650|a620|x670)\b",
            # Compatibilidad
            r"\b(compatib\w*|le\s+hace|le\s+da|le\s+entra|soporta|funciona\s+con|sirve\s+para)\b",
            # Preguntas técnicas
            r"\b(diferencia\s+entre\s+(?:ips|va)|ips\s+o\s+va|panel\s+ips|panel\s+va)\b",
            r"\b(ddr4\s+o\s+ddr5|diferencia\s+entre\s+ddr|memoria\s+ddr[45])\b",
            r"\b(cuello\s+de\s+botella|bottleneck)\b",
            r"\b(cooler|disipador|refrigeraci\w*|ventilador)\b",
            r"\b(fuente\s+de\s+poder|cuantos?\s+watts?|fuente\s+necesito|fuente\s+para)\b",
            r"\b(para\s+(?:programar|programacion|ingenieria|desarrollo|compilar|software|docker))\b",
        ]
        return any(re.search(p, text) for p in patterns)

    def advise(
        self,
        message: str,
        catalog_products: list[dict],
        history: List[dict] | None = None,
    ) -> Tuple[str, list[dict]] | None:
        """Genera una respuesta técnica experta con productos compatibles de la tienda."""
        text = normalize_search(message)

        # ── 1. Placa Intel LGA1700 (B660, H610, B760, Z690, Z790, LGA 1700) ──────
        if re.search(r"\b(b660|h610|b760|z690|z790|lga\s*1700)\b", text) or (
            "placa" in text and any(k in text for k in ("intel", "12100", "13700", "14400"))
        ):
            # Filtrar procesadores Intel LGA1700 en catálogo
            intel_prods = [
                p for p in catalog_products
                if "intel" in normalize_search(p.get("titulo", ""))
                and any(gen in normalize_search(p.get("titulo", "")) for gen in ("12", "13", "14", "12100", "13700", "14400"))
            ]
            msg = (
                "¡Excelente dato! Tu placa madre cuenta con **socket LGA1700**, por lo que es compatible con procesadores **Intel Core de 12ª, 13ª y 14ª generación** "
                "(los procesadores AMD Ryzen no son compatibles con esta placa).\n\n"
                "Para ingeniería de software, programación y multitarea exigente, te recomiendo:\n"
                "• **Intel Core i5 14400F (14ª Gen)** (S/ 760.00): El punto ideal con 10 núcleos para compilar rápido, levantar contenedores Docker y trabajar fluido.\n"
                "• **Intel Core i7 13700F (13ª Gen)** (S/ 1,280.00): Potencia pesada con 16 núcleos para virtualización y proyectos grandes.\n"
                "• **Intel Core i3 12100F (12ª Gen)** (S/ 370.00): Excelente opción económica de entrada.\n\n"
                "¿Tienes algún presupuesto estimado para ayudarte a elegir el ideal? 😊"
            )
            return msg, intel_prods

        # ── 2. Placa AMD Socket AM4 (B450, B550, A520, X570, AM4) ────────────────
        if re.search(r"\b(am4|b450|b550|a520|x570)\b", text):
            am4_prods = [
                p for p in catalog_products
                if any(k in normalize_search(p.get("titulo", "")) for k in ("5600", "5500", "4600", "3600"))
            ]
            msg = (
                "¡Perfecto! Tu placa cuenta con **socket AM4**, compatible con la serie **AMD Ryzen 3000, 4000 y 5000** "
                "(no es compatible con procesadores Intel ni Ryzen 7000/8000 que usan AM5).\n\n"
                "Te recomiendo:\n"
                "• **AMD Ryzen 5 5600GT** (S/ 690.00): Gran rendimiento de 6 núcleos / 12 hilos con gráficos Radeon integrados, rinde excelente tanto para desarrollo como para gaming.\n\n"
                "¿Deseas conocer más detalles o consultar disponibilidad? 🎮"
            )
            return msg, am4_prods

        # ── 3. Placa AMD Socket AM5 (B650, A620, X670, AM5) ───────────────────────
        if re.search(r"\b(am5|b650|a620|x670)\b", text):
            am5_prods = [
                p for p in catalog_products
                if any(k in normalize_search(p.get("titulo", "")) for k in ("8500", "7600", "7700", "7800"))
            ]
            msg = (
                "¡Genial! Tu placa cuenta con **socket AM5** de última generación, compatible con procesadores **AMD Ryzen 7000 y 8000** "
                "y requiere memorias RAM DDR5.\n\n"
                "Una opción destacada en tienda:\n"
                "• **AMD Ryzen 5 8500G** (S/ 545.00): Con arquitectura Zen 4 y gráficos Radeon 740M integrados.\n\n"
                "¿Te gustaría revisar memorias RAM compatibles o fuentes de poder? 🚀"
            )
            return msg, am5_prods

        # ── 4. Dudas de Monitores: Panel IPS vs Panel VA ───────────────────────────
        if re.search(r"\b(ips|va)\b", text) and ("panel" in text or "diferencia" in text or "pantalla" in text or "monitor" in text):
            monitors = [p for p in catalog_products if "monitor" in normalize_search(p.get("categoria", "") + " " + p.get("titulo", ""))]
            msg = (
                "¡Gran pregunta sobre monitores! Aquí la diferencia clave entre ambos paneles:\n\n"
                "• **Panel IPS**: Ofrece los mejores ángulos de visión (178°) y colores más precisos y realistas. Es el panel más recomendado para **programación, diseño gráfico, trabajo prolongado y lectura nítida de código**.\n"
                "• **Panel VA**: Ofrece contrastes mucho más profundos y negros más oscuros. Es excelente para ver películas, jugar de noche en habitaciones con poca luz y juegos cinemáticos.\n\n"
                "En tienda tenemos el **Teros 23.8\" IPS a S/ 270.00** y el **Teros 27\" VA a S/ 345.00**, ambos a 144Hz. ¿Cuál se adapta mejor a tu uso? 👀"
            )
            return msg, monitors

        # ── 5. Dudas de RAM: DDR4 vs DDR5 ─────────────────────────────────────────
        if "ddr4" in text or "ddr5" in text:
            msg = (
                "La diferencia principal entre DDR4 y DDR5 radica en la velocidad y el ancho de banda:\n\n"
                "• **DDR5**: Funciona desde 4800 MHz hasta 6000+ MHz, ideal para compilar proyectos gigantes, renderizado 3D y procesadores de última generación.\n"
                "• **DDR4**: Funciona habitualmente a 3200 MHz, es más económica y sigue ofreciendo un desempeño excelente para la mayoría de juegos y programación.\n\n"
                "⚠️ *Importante:* No son intercambiables físicamente. Tu placa madre determina si acepta DDR4 o DDR5. ¿Sabes cuál modelo de placa tienes?"
            )
            return msg, []

        # ── 6. Dudas de Fuentes de Poder (PSU / Watts) ────────────────────────────
        if re.search(r"\b(fuente|watts?|potencia)\b", text) and any(k in text for k in ("rtx", "gtx", "tarjeta", "grafica", "placa", "necesito", "aguanta")):
            msg = (
                "Para elegir la fuente de poder adecuada, la clave es tu tarjeta de video y procesador:\n\n"
                "• Para **RTX 3060 / 4060**: Recomendamos una fuente de **550W a 650W** con certificación **80 Plus Bronce o Gold**.\n"
                "• Para **RTX 4070 o superior**: Se recomienda desde **750W** en adelante.\n"
                "• Para PCs sin tarjeta gráfica dedicada (gráficos integrados): Una de **450W a 500W** es más que suficiente.\n\n"
                "¿Qué tarjeta gráfica o componentes tienes o piensas instalar? Con gusto te confirmo la potencia ideal ⚡"
            )
            return msg, []

        # ── 7. Cuello de botella ──────────────────────────────────────────────────
        if "cuello de botella" in text or "bottleneck" in text:
            msg = (
                "El cuello de botella ocurre cuando un componente (generalmente el procesador o la tarjeta gráfica) es significativamente más lento que el otro, limitando su rendimiento máximo.\n\n"
                "Para evitarlo, buscamos un balance adecuado: por ejemplo, un **Intel Core i5 14400F** o **Ryzen 5 5600** hace una pareja perfecta con tarjetas como la **RTX 3060 / 4060** sin pérdidas de rendimiento.\n\n"
                "Dime qué procesador y tarjeta gráfica tienes en mente y te calculo si hay balance óptimo 😊"
            )
            return msg, []

        # ── 8. Enfoque Ingeniería de Software / Programación ──────────────────────
        if any(k in text for k in ("ingenieria", "programar", "programacion", "software", "desarrollo", "compilar", "docker")):
            procs = [p for p in catalog_products if "procesador" in normalize_search(p.get("categoria", "") + " " + p.get("titulo", ""))]
            msg = (
                "Para **ingeniería de software y desarrollo**, las prioridades de hardware son:\n\n"
                "1. **Procesador (CPU)**: Buena cantidad de núcleos e hilos para compilar rápido y correr Docker/máquinas virtuales (recomendado: Intel Core i5/i7 o Ryzen 5/7).\n"
                "2. **Memoria RAM**: Mínimo 16 GB, idealmente 32 GB si usas varios IDEs, navegadores y contenedores al mismo tiempo.\n"
                "3. **Almacenamiento**: SSD NVMe rápido para carga instantánea de proyectos y librerías.\n\n"
                "¿Ya tienes algún componente comprado o buscas armar el equipo desde cero? Te ayudo a optimizar cada sol 💻"
            )
            return msg, procs[:5]

        return None
