import math
import re

from app.ai.intent_service import IntentService
from app.ai.llm_service import LLMService
from app.domain.intents import Intent
from app.domain.product_filters import ProductFilters
from app.domain.recommendation_rules import is_processor_request
from app.domain.search_normalizer import normalize_search
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.chat import ChatResponse, ProductSummary
from app.services.commercial_service import CommercialService
from app.services.conversation_context_service import ConversationContextService
from app.services.recommendation_service import RecommendationService


class ChatService:

    OUT_OF_SCOPE_MESSAGE = (
        "¡Hola! Soy Eli 😊 Estoy aquí para ayudarte con todo lo relacionado a Eagle Gaming: "
        "precios, stock, características, garantías y envíos. ¿Qué producto estás buscando?"
    )

    # ─── Helpers de número ──────────────────────────────────────────────────────

    @staticmethod
    def _number(value, *, integer=False):
        if value is None or isinstance(value, bool):
            return None
        try:
            number = float(str(value).replace("S/", "").replace(",", "").strip())
            if not math.isfinite(number) or number < 0:
                return None
            if integer:
                return int(number) if number.is_integer() else None
            return number
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _product_summary(product: dict) -> str | None:
        fields = (
            "procesador", "memoria_ram", "tarjeta_de_video", "graficos",
            "pantalla", "almacenamiento",
        )
        details = [str(product[field]).strip() for field in fields if product.get(field)]
        return " · ".join(details[:2]) or None

    def _to_product_summary(self, product: dict) -> ProductSummary:
        return ProductSummary(
            id=str(product["id"]),
            name=product.get("titulo") or "Producto sin título",
            summary=self._product_summary(product),
            price=self._number(product.get("precio")),
            stock=self._number(product.get("stock"), integer=True),
            product_url=product.get("url") or None,
        )

    # ─── Constructor ────────────────────────────────────────────────────────────

    def __init__(
        self,
        product_service=None,
        llm_service=None,
        context_service=None,
        conversation_repo=None,
    ):
        self.intent_service = IntentService()
        self.product_service = product_service
        self.llm_service = llm_service if llm_service is not None else LLMService()
        self.commercial_service = CommercialService()
        self.context_service = context_service or ConversationContextService()
        self.conversation_repo = conversation_repo or ConversationRepository()

    # ─── Lazy product service ───────────────────────────────────────────────────

    def _ensure_product_service(self):
        if self.product_service is None:
            from app.services.product_service import ProductService
            self.product_service = ProductService()

    # ─── Quick Replies automáticos ──────────────────────────────────────────────

    @staticmethod
    def _generate_quick_replies(intent: Intent, has_products: bool) -> list[str]:
        if intent == Intent.GREETING:
            return ["Laptops gamer", "PCs completas", "Monitores 144Hz", "Envíos a provincia"]
        if intent == Intent.COMMERCIAL_INFO:
            return ["¿Tienen tienda física?", "¿Cómo hago el pago?", "Ver laptops", "Ver PCs"]
        if intent == Intent.RECOMMENDATION:
            return ["Presupuesto de S/ 2500", "Presupuesto de S/ 3500", "Laptops para estudio", "PC Gamer"]
        if intent == Intent.COMPARISON:
            return ["Ver precios", "¿Tienen stock?", "¿Tienen garantía?"]
        if has_products:
            return ["¿Cuál es el costo de envío?", "¿Tienen garantía?", "¿Cómo se paga?"]
        return ["Laptops", "PCs armadas", "Procesadores", "Monitores"]

    # ─── Respuestas del catálogo ────────────────────────────────────────────────

    async def _catalog_response(
        self,
        message: str,
        intent: Intent,
        query: str | None = None,
        history: list[dict] | None = None,
        session_id: str | None = None,
    ) -> ChatResponse:
        if query is None:
            query = self.intent_service.extract_product_query(message)
        if not query and session_id:
            query = self.context_service.get_last_product_query(session_id)
        if not query:
            return ChatResponse(
                message="¿Qué producto o modelo estás buscando? Puedo ayudarte con precios, stock y características 😊",
                intent=intent.value, resolved=False,
                quick_replies=self._generate_quick_replies(intent, False),
            )
        self._ensure_product_service()
        products = self.product_service.search_products(ProductFilters(texto=query))
        if not products:
            return ChatResponse(
                message=f"No encontré resultados para '{query}'. Prueba con la marca, modelo o categoría. ¡Puedo ayudarte a buscar de otra forma!",
                intent=intent.value, resolved=False,
                quick_replies=self._generate_quick_replies(intent, False),
            )
        if session_id:
            self.context_service.set_last_product_query(session_id, query)
        shown_products = products[:5]
        summaries = [self._to_product_summary(p) for p in shown_products]
        multiple = len(products) > 1

        # Generar fallback base estructurado
        if intent in {Intent.FEATURES, Intent.WARRANTY} and not multiple:
            product = shown_products[0]
            if intent == Intent.WARRANTY:
                detail = str(product.get("garantia") or "Garantía no informada; confirma con la tienda.")
                resolved = bool(product.get("garantia"))
                fallback_msg = f"*{summaries[0].name}* tiene {detail}. ¡Recuerda que la garantía te protege en caso de fallas de fábrica! 🛡️"
            else:
                detail = self._product_summary(product) or "Ficha técnica no informada."
                resolved = detail != "Ficha técnica no informada."
                fallback_msg = f"*{summaries[0].name}*: {detail}. ¿Te interesa ver el precio o consultar disponibilidad?"
        elif intent == Intent.AVAILABILITY and not multiple:
            stock = summaries[0].stock
            if stock is not None and stock > 0:
                fallback_msg = f"¡Sí! *{summaries[0].name}* está disponible — Stock registrado: {stock} unidades. ¿Te gustaría conocer el precio? 🎮"
                resolved = True
            elif stock == 0:
                fallback_msg = f"Lo siento, *{summaries[0].name}* está agotado por el momento. ¿Quieres que te muestre opciones similares?"
                resolved = True
            else:
                fallback_msg = f"El stock de *{summaries[0].name}* no está registrado en este momento. Te recomiendo confirmar con la tienda. ¿Puedo ayudarte con algo más?"
                resolved = False
        elif intent == Intent.PRICE and not multiple:
            price = summaries[0].price
            if price is not None:
                fallback_msg = f"*{summaries[0].name}* tiene un precio de S/ {price:,.2f}. ¡Excelente opción! ¿Quieres ver las características o consultar disponibilidad? 🛒"
                resolved = True
            else:
                fallback_msg = f"El precio de *{summaries[0].name}* no está registrado. Te recomiendo consultar directamente con la tienda para el precio actualizado."
                resolved = False
        else:
            labels = {
                Intent.PRICE: "Aquí tienes los precios disponibles. ¿Alguno te llama la atención? 💰",
                Intent.AVAILABILITY: "Te muestro las opciones disponibles. ¿Cuál te interesa? 🎮",
                Intent.FEATURES: "Aquí están las fichas técnicas. ¿Quieres saber más sobre alguno? 🔧",
                Intent.WARRANTY: "Selecciona un producto para consultar su garantía. 🛡️",
                Intent.PRODUCT_SEARCH: "Encontré estas opciones para ti. ¿Cuál te llama más la atención? 👀",
            }
            count = len(summaries)
            fallback_msg = f"Encontré {count} {'opción' if count == 1 else 'opciones'}. {labels.get(intent, 'Elige una para más detalles.')}"
            resolved = len(products) == 1 and intent == Intent.PRODUCT_SEARCH
            if len(products) > 5:
                fallback_msg += " Mostrando las primeras 5; indícame marca o modelo para afinar la búsqueda."
                resolved = False

        # Intentar síntesis en lenguaje natural humano con Gemini
        natural_msg = None
        if hasattr(self.llm_service, "generate_response"):
            products_context = [
                {
                    "nombre": p.get("titulo") or "Producto sin título",
                    "precio": p.get("precio"),
                    "stock": p.get("stock"),
                    "garantia": p.get("garantia"),
                    "procesador": p.get("procesador"),
                    "memoria_ram": p.get("memoria_ram"),
                    "graficos": p.get("graficos") or p.get("tarjeta_de_video"),
                    "almacenamiento": p.get("almacenamiento"),
                    "pantalla": p.get("pantalla"),
                }
                for p in shown_products
            ]
            try:
                gen_call = self.llm_service.generate_response(
                    user_message=message,
                    intent=intent.value,
                    products_context=products_context,
                    history=history,
                )
                import inspect
                res = await gen_call if inspect.isawaitable(gen_call) else gen_call
                natural_msg = res if isinstance(res, str) and res.strip() else None
            except Exception:
                natural_msg = None

        final_message = natural_msg if isinstance(natural_msg, str) and natural_msg.strip() else fallback_msg
        return ChatResponse(
            message=final_message,
            intent=intent.value,
            resolved=resolved,
            products=summaries,
            quick_replies=self._generate_quick_replies(intent, bool(summaries)),
        )

    # ─── Comparación de productos ──────────────────────────────────────────────

    async def _compare_products(self, message: str, history: list[dict] | None = None) -> ChatResponse:
        self._ensure_product_service()
        # Buscamos términos potenciales de los 2 productos dividiendo por vs o y
        clean = normalize_search(message)
        parts = re.split(r"\b(?:vs|versus|o|y)\b", clean)
        candidates = []
        for part in parts:
            q = self.intent_service.extract_product_query(part)
            if q:
                found = self.product_service.search_products(ProductFilters(texto=q))
                if found and found[0] not in candidates:
                    candidates.append(found[0])

        if len(candidates) < 2:
            # Intentamos buscar todos los productos coincidentes con la consulta completa
            full_query = self.intent_service.extract_product_query(message)
            candidates = self.product_service.search_products(ProductFilters(texto=full_query))[:2]

        summaries = [self._to_product_summary(p) for p in candidates]
        fallback_msg = (
            f"Comparativa entre opciones: encontré {len(summaries)} productos para comparar. "
            "Revisa sus fichas y precios a continuación para ver cuál se ajusta mejor a tus necesidades 🎮."
            if summaries else "Indícame los dos modelos o componentes que te gustaría comparar (ej: RTX 4060 vs RTX 3060)."
        )

        natural_msg = None
        if summaries and hasattr(self.llm_service, "generate_response"):
            products_context = [
                {
                    "nombre": p.get("titulo") or "Producto sin título",
                    "precio": p.get("precio"),
                    "stock": p.get("stock"),
                    "garantia": p.get("garantia"),
                    "procesador": p.get("procesador"),
                    "memoria_ram": p.get("memoria_ram"),
                    "graficos": p.get("graficos") or p.get("tarjeta_de_video"),
                    "almacenamiento": p.get("almacenamiento"),
                }
                for p in candidates
            ]
            try:
                gen_call = self.llm_service.generate_response(
                    user_message=message,
                    intent=Intent.COMPARISON.value,
                    products_context=products_context,
                    history=history,
                )
                import inspect
                res = await gen_call if inspect.isawaitable(gen_call) else gen_call
                natural_msg = res if isinstance(res, str) and res.strip() else None
            except Exception:
                natural_msg = None

        final_msg = natural_msg if isinstance(natural_msg, str) and natural_msg.strip() else fallback_msg
        return ChatResponse(
            message=final_msg,
            intent=Intent.COMPARISON.value,
            resolved=len(summaries) >= 2,
            products=summaries,
            quick_replies=self._generate_quick_replies(Intent.COMPARISON, bool(summaries)),
        )

    # ─── Recomendación de procesadores ─────────────────────────────────────────

    def _recommend_processors(self, message: str) -> ChatResponse:
        self._ensure_product_service()
        options = RecommendationService(self.product_service).processor_options(message)
        summaries = [self._to_product_summary(p) for p in options]
        summaries = [p for p in summaries if p.stock is None or p.stock > 0]
        msg = (
            "¡Claro! Te dejo las mejores opciones de procesadores de nuestro catálogo 🎮 "
            "Para recomendarte el ideal, cuéntame: ¿cuál es tu presupuesto y ya tienes placa madre?"
            if summaries else
            "No encontré procesadores disponibles para esa consulta en este momento. ¿Quieres buscar por otra categoría?"
        )
        return ChatResponse(
            message=msg,
            intent=Intent.RECOMMENDATION.value,
            resolved=False,
            products=summaries,
            quick_replies=["Tengo placa AM4", "Tengo placa LGA1700", "Presupuesto S/ 800", "Presupuesto S/ 1500"],
        )

    # ─── Parseo de contexto para recomendación ──────────────────────────────────

    @staticmethod
    def _recommendation_choice(message: str) -> str | None:
        text = normalize_search(message)
        laptop = "laptop" in text
        pc = "pc" in text or "computadora" in text
        if laptop and pc:
            return "compare"
        if laptop:
            return "laptop"
        if pc:
            return "pc"
        return None

    @staticmethod
    def _recommendation_budget(message: str) -> int | None:
        match = re.search(r"\b(?:s\s*)?(\d{3,6})(?:\s*soles)?\b", normalize_search(message))
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_budget_range(message: str) -> tuple[float | None, float | None]:
        text = normalize_search(message)
        range_match = re.search(
            r"\b(?:entre|de|desde)\s*(?:s\s*)?(\d{3,6})\s*(?:y|a|hasta)\s*(?:s\s*)?(\d{3,6})\b",
            text,
        )
        if range_match:
            min_val = float(range_match.group(1))
            max_val = float(range_match.group(2))
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            return min_val, max_val

        max_match = re.search(r"\b(?:hasta|maximo|menor a)\s*(?:s\s*)?(\d{3,6})\b", text)
        if max_match:
            return None, float(max_match.group(1))

        min_match = re.search(r"\b(?:desde|minimo|mayor a)\s*(?:s\s*)?(\d{3,6})\b", text)
        if min_match:
            return float(min_match.group(1)), None

        return None, None

    def _recommend_for_context(self, message: str, session_id: str | None) -> ChatResponse:
        current = self.context_service.get_recommendation(session_id)
        choice = self._recommendation_choice(message) or (current.product_choice if current else None)
        budget = self._recommendation_budget(message) or (current.budget if current else None)
        context = self.context_service.update_recommendation(
            session_id, product_choice=choice, budget=budget
        )

        if context.product_choice == "compare":
            return ChatResponse(
                message=(
                    "¡Buena pregunta! 💻🖥️ Para estudiar y trabajar, una laptop te da movilidad total; "
                    "una PC te permite mejorar componentes con más facilidad y suele dar más potencia por el precio. "
                    "¿Cuál prefieres: laptop o PC?"
                ),
                intent=Intent.RECOMMENDATION.value, resolved=False, products=[],
                quick_replies=["Prefiero Laptop", "Prefiero PC Gamer"],
            )
        if not context.product_choice:
            return ChatResponse(
                message="¡Con gusto te ayudo! ¿Estás buscando laptop o PC? Y si me dices tu presupuesto, puedo afinar las opciones 😊",
                intent=Intent.RECOMMENDATION.value, resolved=False, products=[],
                quick_replies=["Laptop", "PC de escritorio", "Quiero comparar ambas"],
            )
        if context.budget is None:
            return ChatResponse(
                message=f"Perfecto, buscaré la mejor {context.product_choice} para ti 🎯 ¿Cuál es tu presupuesto en soles?",
                intent=Intent.RECOMMENDATION.value, resolved=False, products=[],
                quick_replies=["Hasta S/ 2500", "Hasta S/ 3500", "Más de S/ 4000"],
            )

        self._ensure_product_service()
        category = "laptop" if context.product_choice == "laptop" else "pc"
        p_min, p_max = self._extract_budget_range(message)
        if p_max is None:
            p_max = float(context.budget)

        products = self.product_service.search_products(
            ProductFilters(categoria=category, precio_min=p_min, precio_max=p_max)
        )
        summaries = [self._to_product_summary(p) for p in products[:5]]
        if not summaries:
            msg = (
                f"Mmm, no encontré {context.product_choice}s dentro de S/ {context.budget:,.0f} en este momento 😕 "
                "¿Quieres ajustar el presupuesto o buscar en otra categoría?"
            )
        else:
            msg = (
                f"¡Aquí tienes las mejores opciones de {context.product_choice} dentro de tu presupuesto! 🚀 "
                "Todas cuentan con garantía. Elige la que más te guste y te cuento más detalles."
            )
        return ChatResponse(
            message=msg,
            intent=Intent.RECOMMENDATION.value,
            resolved=False,
            products=summaries,
            quick_replies=["¿Cómo se paga?", "¿Hacen envíos a provincia?", "¿Tienen garantía?"],
        )

    # ─── Proceso principal ──────────────────────────────────────────────────────

    async def process_message(
        self,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> ChatResponse:
        import time
        start_time = time.perf_counter()

        clean_message = message.strip()

        if not clean_message:
            raise ValueError("El mensaje no puede estar vacío.")

        # ── 0. Bloqueo de prompt injection ────────────────────────────────────
        if self.intent_service.is_injection_attempt(clean_message):
            injection_resp = ChatResponse(
                message=(
                    "Soy Eli, la asesora de Eagle Gaming 😊 Solo puedo ayudarte con "
                    "productos, precios, stock y envíos. ¿Qué equipo estás buscando?"
                ),
                intent=Intent.UNKNOWN.value,
                resolved=False,
                products=[],
                quick_replies=["Laptops", "PCs Armadas", "Monitores", "Componentes"],
            )
            self._save_turn_to_db(session_id, clean_message, injection_resp, start_time, user_id)
            return injection_resp

        # Recuperar historial para contexto
        history = [
            {"role": t.role, "text": t.text}
            for t in self.context_service.get_history(session_id)
        ]

        # Registrar el mensaje del usuario
        self.context_service.add_turn(session_id, "user", clean_message)

        # ── 1. Información comercial ───────────────────────────────────────────
        commercial_answer = self.commercial_service.answer(clean_message)
        if commercial_answer is not None:
            self.context_service.add_turn(session_id, "assistant", commercial_answer.message)
            resp = ChatResponse(
                message=commercial_answer.message,
                intent=Intent.COMMERCIAL_INFO.value,
                resolved=commercial_answer.resolved,
                products=[],
                quick_replies=self._generate_quick_replies(Intent.COMMERCIAL_INFO, False),
            )
            self._save_turn_to_db(session_id, clean_message, resp, start_time, user_id)
            return resp

        # ── 2. Fuera de ámbito ─────────────────────────────────────────────────
        if self.intent_service.is_out_of_scope(clean_message):
            self.context_service.add_turn(session_id, "assistant", self.OUT_OF_SCOPE_MESSAGE)
            resp = ChatResponse(
                message=self.OUT_OF_SCOPE_MESSAGE,
                intent=Intent.UNKNOWN.value,
                resolved=False,
                products=[],
                quick_replies=["Laptops", "PCs Armadas", "Monitores", "Componentes"],
            )
            self._save_turn_to_db(session_id, clean_message, resp, start_time, user_id)
            return resp

        # ── 3. Detectar intención ──────────────────────────────────────────────
        intent = self.intent_service.detect_intent(clean_message)
        current_context = self.context_service.get_recommendation(session_id)

        # ── 3a. Armar PC → redirige a la sección del sitio ────────────────────
        if intent == Intent.BUILD_PC:
            from app.core.config import settings
            build_url = settings.BUILD_PC_URL
            build_msg = (
                f"¡Genial! 🛠️ Tenemos una sección especial para que armes tu PC ideal. "
                f"Visita nuestra página **Arma tu PC** donde puedes elegir componentes "
                f"compatibles, ver precios y configurar tu equipo a medida: {build_url} "
                f"¿Te ayudo también a revisar el precio de algún componente en particular? 😊"
            )
            self.context_service.add_turn(session_id, "assistant", build_msg)
            resp = ChatResponse(
                message=build_msg,
                intent=Intent.BUILD_PC.value,
                resolved=True,
                products=[],
                quick_replies=["Ver procesadores", "Ver GPUs", "Ver memorias RAM", "Ver precios"],
            )
            self._save_turn_to_db(session_id, clean_message, resp, start_time, user_id)
            return resp

        if intent == Intent.COMPARISON:
            resp = await self._compare_products(clean_message, history=history)
            self.context_service.add_turn(session_id, "assistant", resp.message)
            self._save_turn_to_db(session_id, clean_message, resp, start_time, user_id)
            return resp

        if intent == Intent.RECOMMENDATION or (
            current_context and (
                self._recommendation_choice(clean_message) is not None
                or self._recommendation_budget(clean_message) is not None
            )
        ):
            resp = self._recommend_for_context(clean_message, session_id)
            self.context_service.add_turn(session_id, "assistant", resp.message)
            self._save_turn_to_db(session_id, clean_message, resp, start_time, user_id)
            return resp

        # ── 4. Gemini para intenciones desconocidas (con historial) ───────────
        interpretation = (
            await self.llm_service.interpret(clean_message, history=history)
            if intent == Intent.UNKNOWN
            else None
        )
        query = None
        if interpretation is not None:
            intent = interpretation.intent
            query = interpretation.query.strip()

        if is_processor_request(clean_message) and (
            intent == Intent.RECOMMENDATION
            or re.search(r'\b(juego\w*|jugar|gaming|gamer)\b', clean_message.lower())
        ):
            resp = self._recommend_processors(clean_message)
            self.context_service.add_turn(session_id, "assistant", resp.message)
            self._save_turn_to_db(session_id, clean_message, resp, start_time, user_id)
            return resp

        if intent in {Intent.PRICE, Intent.AVAILABILITY, Intent.FEATURES, Intent.WARRANTY, Intent.PRODUCT_SEARCH}:
            resp = await self._catalog_response(
                clean_message, intent, query, history=history, session_id=session_id
            )
            self.context_service.add_turn(session_id, "assistant", resp.message)
            self._save_turn_to_db(session_id, clean_message, resp, start_time, user_id)
            return resp

        # ── 5. Respuestas por defecto ──────────────────────────────────────────
        responses = {
            Intent.GREETING: (
                "¡Hola! Soy Eli, tu asesora de Eagle Gaming 👋 "
                "¿Estás buscando una PC, laptop, monitor, procesador u otro componente? ¡Con mucho gusto te ayudo!"
            ),
            Intent.RECOMMENDATION: (
                "¡Claro! Para recomendarte lo mejor, cuéntame: ¿para qué usarás el equipo y cuál es tu presupuesto? 😊"
            ),
            Intent.UNKNOWN: self.OUT_OF_SCOPE_MESSAGE,
            Intent.PRICE: "¿De qué producto quieres saber el precio? Indícame la marca o modelo 😊",
            Intent.AVAILABILITY: "¿De qué producto quieres saber el stock? Dime la marca o modelo.",
            Intent.FEATURES: "¿De qué producto quieres conocer las características? Indícame la marca o modelo.",
            Intent.WARRANTY: "¿De qué producto quieres saber la garantía? Dime la marca o modelo.",
            Intent.PRODUCT_SEARCH: "¿Qué producto estás buscando? Dime la marca, modelo o categoría.",
        }
        msg = responses.get(intent, self.OUT_OF_SCOPE_MESSAGE)
        self.context_service.add_turn(session_id, "assistant", msg)
        resp = ChatResponse(
            message=msg,
            intent=intent.value,
            resolved=intent == Intent.GREETING,
            products=[],
            quick_replies=self._generate_quick_replies(intent, False),
        )
        self._save_turn_to_db(session_id, clean_message, resp, start_time, user_id)
        return resp

    def _save_turn_to_db(
        self,
        session_id: str | None,
        user_message: str,
        response: ChatResponse,
        start_time: float,
        user_id: str | None = None,
    ) -> None:
        import time
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.response_time_ms = elapsed_ms

        if not session_id or not self.conversation_repo:
            return
        try:
            prod_dicts = [p.model_dump() for p in response.products] if response.products else []
            self.conversation_repo.save_message(
                session_id=session_id,
                user_message=user_message,
                assistant_message=response.message,
                intent=response.intent,
                resolved=response.resolved,
                products=prod_dicts,
                response_time_ms=elapsed_ms,
                user_id=user_id,
            )
        except Exception:
            pass
