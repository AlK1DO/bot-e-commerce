from app.domain.commercial_information import (
    COMMERCIAL_ANSWERS,
    CommercialAnswer,
    detect_commercial_topic,
)


class CommercialService:
    def answer(self, message: str) -> CommercialAnswer | None:
        topic = detect_commercial_topic(message)
        return COMMERCIAL_ANSWERS.get(topic) if topic else None
