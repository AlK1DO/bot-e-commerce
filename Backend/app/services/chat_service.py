from app.schemas.chat import ChatResponse, ProductSummary
from app.domain.product_filters import ProductFilters
import math
from app.ai.intent_service import IntentService
from app.domain.intents import Intent
from app.ai.llm_service import LLMService
from app.domain.recommendation_rules import is_processor_request
from app.services.recommendation_service import RecommendationService
from app.services.commercial_service import CommercialService
from app.services.conversation_context_service import ConversationContextService
from app.domain.search_normalizer import normalize_search
import re


class ChatService:

    OUT_OF_SCOPE_MESSAGE = (
        "Estoy aquí para ayudarte con consultas de Eagle Gaming Perú y buscar "
        "productos tecnológicos. Puedo ayudarte con precios, disponibilidad, "
        "características, garantías, envíos y recojo. ¿Qué producto o consulta de la tienda necesitas?"
    )

    def __init__(self, product_service=None, llm_service=None, context_service=None):
        self.intent_service = IntentService()
        self.product_service = product_service
        self.llm_service = llm_service if llm_service is not None else LLMService()
        self.commercial_service = CommercialService()
        self.context_service = context_service or ConversationContextService()

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

    def _catalog_response(self, message, intent, query=None):
        if query is None:
            query = self.intent_service.extract_product_query(message)
        if not query:
            return ChatResponse(message="¿Qué producto o modelo quieres consultar?", intent=intent.value, resolved=False)
        if self.product_service is None:
            from app.services.product_service import ProductService
            self.product_service = ProductService()
        products = self.product_service.search_products(ProductFilters(texto=query))
        if not products:
            return ChatResponse(message="No encontré productos para esa búsqueda. Prueba con la marca o el modelo.", intent=intent.value, resolved=False)
        shown_products = products[:5]
        summaries = [self._to_product_summary(product) for product in shown_products]
        multiple = len(products) > 1
        if intent in {Intent.FEATURES, Intent.WARRANTY} and not multiple:
            product = shown_products[0]
            if intent == Intent.WARRANTY:
                detail = str(product.get("garantia") or "Garantía no informada; confirma con la tienda.")
                resolved = bool(product.get("garantia"))
            else:
                detail = self._product_summary(product) or "Ficha técnica no informada."
                resolved = detail != "Ficha técnica no informada."
            message = f"{summaries[0].name}: {detail}"
        elif intent == Intent.AVAILABILITY and not multiple:
            stock = summaries[0].stock
            detail = f"Stock registrado: {stock}." if stock is not None else "Stock no informado; confirma con la tienda."
            message, resolved = f"{summaries[0].name}: {detail}", stock is not None
        elif intent == Intent.PRICE and not multiple:
            price = summaries[0].price
            detail = f"S/ {price:.2f}." if price is not None else "Precio no informado."
            message, resolved = f"{summaries[0].name}: {detail}", price is not None
        else:
            labels = {
                Intent.PRICE: "Revisa los precios en las tarjetas.",
                Intent.AVAILABILITY: "Elige un producto para confirmar su disponibilidad.",
                Intent.FEATURES: "Elige un producto para ver su ficha técnica.",
                Intent.WARRANTY: "Elige un producto para consultar su garantía.",
                Intent.PRODUCT_SEARCH: "Elige una opción para ver más detalles.",
            }
            count = len(summaries)
            message = f"Encontré {count} {'opción' if count == 1 else 'opciones'}. {labels[intent]}"
            resolved = len(products) == 1 and intent == Intent.PRODUCT_SEARCH
        if len(products) > 5:
            message += " Muestra solo cinco; indica marca o modelo para afinar la búsqueda."
            resolved = False
        return ChatResponse(message=message, intent=intent.value, resolved=resolved, products=summaries)

    def _recommend_processors(self, message):
        if self.product_service is None:
            from app.services.product_service import ProductService
            self.product_service = ProductService()
        options = RecommendationService(self.product_service).processor_options(message)
        summaries = [self._to_product_summary(product) for product in options]
        # No se ofrecen productos explícitamente agotados como opciones disponibles.
        summaries = [p for p in summaries if p.stock is None or p.stock > 0]
        message = (
            "Te dejo opciones del catálogo. Para recomendarte una, "
            "¿cuál es tu presupuesto y ya tienes placa madre?"
            if summaries else "No encontré procesadores para esa consulta."
        )
        return ChatResponse(message=message, intent=Intent.RECOMMENDATION.value,
                            resolved=False, products=summaries)

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

    def _recommend_for_context(self, message: str, session_id: str | None):
        current = self.context_service.get_recommendation(session_id)
        choice = self._recommendation_choice(message) or (current.product_choice if current else None)
        budget = self._recommendation_budget(message) or (current.budget if current else None)
        context = self.context_service.update_recommendation(
            session_id, product_choice=choice, budget=budget
        )
        if context.product_choice == "compare":
            return ChatResponse(
                message=("Para estudiar y trabajar, una laptop te da movilidad; una PC permite "
                         "mejorar componentes con más facilidad. ¿Cuál prefieres: laptop o PC?"),
                intent=Intent.RECOMMENDATION.value, resolved=False, products=[]
            )
        if not context.product_choice:
            return ChatResponse(
                message="¿Prefieres laptop o PC? También indícame tu presupuesto.",
                intent=Intent.RECOMMENDATION.value, resolved=False, products=[]
            )
        if context.budget is None:
            return ChatResponse(
                message=f"Perfecto, buscaré una {context.product_choice}. ¿Cuál es tu presupuesto en soles?",
                intent=Intent.RECOMMENDATION.value, resolved=False, products=[]
            )
        if self.product_service is None:
            from app.services.product_service import ProductService
            self.product_service = ProductService()
        category = "laptop" if context.product_choice == "laptop" else "pc"
        products = self.product_service.search_products(
            ProductFilters(categoria=category, precio_max=context.budget)
        )
        summaries = [self._to_product_summary(product) for product in products[:5]]
        if not summaries:
            message = f"No encontré {context.product_choice}s dentro de S/ {context.budget:.2f}. ¿Deseas ajustar el presupuesto?"
        else:
            message = (
                "Estas son opciones de nuestro catálogo dentro de tu presupuesto. "
                "Puedes revisar sus detalles y decirme cuál te interesa."
            )
        return ChatResponse(message=message, intent=Intent.RECOMMENDATION.value,
                            resolved=False, products=summaries)

    def process_message(
        self,
        message: str,
        session_id: str | None = None
    ) -> ChatResponse:

        clean_message = message.strip()

        if not clean_message:
            raise ValueError("El mensaje no puede estar vacío.")

        commercial_answer = self.commercial_service.answer(clean_message)
        if commercial_answer is not None:
            return ChatResponse(
                message=commercial_answer.message,
                intent=Intent.COMMERCIAL_INFO.value,
                resolved=commercial_answer.resolved,
                products=[],
            )

        if self.intent_service.is_out_of_scope(clean_message):
            return ChatResponse(
                message=self.OUT_OF_SCOPE_MESSAGE,
                intent=Intent.UNKNOWN.value,
                resolved=False,
                products=[],
            )

        intent = self.intent_service.detect_intent(clean_message)
        current_context = self.context_service.get_recommendation(session_id)
        if intent == Intent.RECOMMENDATION or (
            current_context and (
                self._recommendation_choice(clean_message) is not None
                or self._recommendation_budget(clean_message) is not None
            )
        ):
            return self._recommend_for_context(clean_message, session_id)
        # Las consultas conocidas se resuelven de inmediato. Gemini se reserva para
        # recomendaciones y frases que las reglas todavía no pueden interpretar.
        interpretation = (
            self.llm_service.interpret(clean_message)
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
            return self._recommend_processors(clean_message)
        if intent in {Intent.PRICE, Intent.AVAILABILITY, Intent.FEATURES, Intent.WARRANTY, Intent.PRODUCT_SEARCH}:
            return self._catalog_response(clean_message, intent, query)
        responses = {
            Intent.GREETING: "¡Hola! Soy Eli, asesora virtual de Eagle Gaming. ¿Buscas una PC, laptop, monitor o componente?",
            Intent.PRICE: "Entendí que quieres consultar un precio. Aún no he consultado el catálogo para responderte.",
            Intent.AVAILABILITY: "Entendí que quieres consultar disponibilidad. Aún no he verificado el stock.",
            Intent.FEATURES: "Entendí que quieres conocer las características de un producto. Aún no he consultado su ficha.",
            Intent.WARRANTY: "Entendí que quieres consultar una garantía. Aún no he verificado las condiciones del producto.",
            Intent.RECOMMENDATION: "Entendí que buscas una recomendación. ¿Para qué usarás el producto y cuál es tu presupuesto?",
            Intent.PRODUCT_SEARCH: "Entendí que buscas un producto. Aún no he consultado el catálogo para este mensaje.",
            Intent.UNKNOWN: self.OUT_OF_SCOPE_MESSAGE,
        }
        return ChatResponse(
            message=responses[intent],
            intent=intent.value,
            resolved=intent == Intent.GREETING,
            products=[]
        )
