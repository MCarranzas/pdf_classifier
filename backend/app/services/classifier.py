from dataclasses import dataclass
import unicodedata

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "FACTURA": [
        "factura", "n° de factura", "facturar a", "importe",
    ],
    "CONTRATO": ["CONTRATO", "CÓDIGO", "OBJETO DEL CONTRATO", "PARTES CONTRATANTES"],
    "FORMULARIO 110": [
        "Funcionario Dependiente",
        "Anexo al Form 610",
        "Anexo al Form 702",
        "Anexo al Form 510",
    ],
    "OTRO": [],
}

REVIEW_CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class ClassificationResult:
    clasificacion: str
    confianza: float
    motivo: str
    requiere_revision: bool
    matches: list[str]


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def matching_keywords(text: str, keywords: list[str]) -> list[str]:
    normalized = _normalize(text)
    return [keyword for keyword in keywords if _normalize(keyword) in normalized]


def _build_reason(
    category: str,
    matches: list[str],
    tied_categories: list[str],
    requiere_revision: bool,
) -> str:
    if category == "OTRO":
        categorias = ", ".join(
            item.lower() for item in CATEGORY_KEYWORDS if item != "OTRO"
        )
        return f"La primera página no contiene indicadores suficientes de {categorias}."

    if tied_categories:
        categories = " y ".join(item.lower() for item in tied_categories)
        return f"La primera página contiene indicadores de {categories}; se requiere revisión."

    indicators = ", ".join(matches)
    reason = f"La primera página contiene indicadores de {category.lower()}: {indicators}."
    if requiere_revision:
        reason += " La evidencia es limitada y se requiere revisión."
    return reason


def classify_with_details(text: str) -> ClassificationResult:
    matches_by_category = {
        category: matching_keywords(text, keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    scores = {
        category: len(matches)
        for category, matches in matches_by_category.items()
    }
    positive_categories = [category for category, score in scores.items() if score > 0]

    if not positive_categories:
        return ClassificationResult(
            clasificacion="OTRO",
            confianza=0.0,
            motivo=_build_reason("OTRO", [], [], True),
            requiere_revision=True,
            matches=[],
        )

    best_score = max(scores[category] for category in positive_categories)
    best_categories = [
        category
        for category in positive_categories
        if scores[category] == best_score
    ]
    best = best_categories[0]
    confidence = min(best_score / 5, 1.0)
    requiere_revision = (
        len(best_categories) > 1
        or confidence < REVIEW_CONFIDENCE_THRESHOLD
    )
    motivo = _build_reason(
        best,
        matches_by_category[best],
        best_categories if len(best_categories) > 1 else [],
        requiere_revision,
    )
    return ClassificationResult(
        clasificacion=best,
        confianza=round(confidence, 2),
        motivo=motivo,
        requiere_revision=requiere_revision,
        matches=matches_by_category[best],
    )


def classify(text: str) -> tuple[str, float]:
    result = classify_with_details(text)
    return result.clasificacion, result.confianza


def classify_document(text: str) -> ClassificationResult:
    from ..config import get_settings
    from .llm_client import classify_with_ai

    result = classify_with_ai(text)
    if result is not None:
        return result

    if get_settings().ai_fallback_to_keywords:
        return classify_with_details(text)

    return ClassificationResult(
        clasificacion="OTRO",
        confianza=0.0,
        motivo="La clasificación automática no está disponible.",
        requiere_revision=True,
        matches=[],
    )
