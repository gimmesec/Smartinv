"""
Фиксированные классы состояния актива по фото (slug = имя папки при разметке).

Папки для обучения: см. CONDITION_TRAINING_DATA_DIR (по умолчанию рядом с проектом:
``<каталог manage.py>/training_data/asset_condition/<slug>/``).
"""

from __future__ import annotations

from typing import TypedDict


class ConditionClass(TypedDict):
    slug: str
    label_ru: str
    description_ru: str


# Порядок фиксирован: индекс = метка при обучении.
CONDITION_CLASSES: tuple[ConditionClass, ...] = (
    {
        "slug": "ok",
        "label_ru": "Исправен",
        "description_ru": "Внешний вид удовлетворительный, без заметных повреждений.",
    },
    {
        "slug": "damage",
        "label_ru": "Повреждён",
        "description_ru": "Есть видимые повреждения (сколы, трещины, вмятины и т.п.).",
    },
    {
        "slug": "severe",
        "label_ru": "Сильные повреждения",
        "description_ru": "Существенные повреждения, по виду объект нельзя считать исправным.",
    },
    {
        "slug": "unclear",
        "label_ru": "Не определить по фото",
        "description_ru": "Кадр неинформативен: плохой ракурс, размытие, засвет, объект не в кадре.",
    },
)

NUM_CONDITION_CLASSES = len(CONDITION_CLASSES)

CLASS_SLUGS: tuple[str, ...] = tuple(c["slug"] for c in CONDITION_CLASSES)
CLASS_LABELS_RU: tuple[str, ...] = tuple(c["label_ru"] for c in CONDITION_CLASSES)


def slug_to_index(slug: str) -> int | None:
    try:
        return CLASS_SLUGS.index(slug)
    except ValueError:
        return None


def classes_reference_for_prompt() -> str:
    lines = [f"Фиксированные классы состояния по фотографии ({NUM_CONDITION_CLASSES} шт.):"]

    for i, c in enumerate(CONDITION_CLASSES, start=1):
        lines.append(
            f"{i}) `{c['slug']}` — {c['label_ru']}: {c['description_ru']}"
        )

    return "\n".join(lines)


def gigachat_condition_system_prompt() -> str:
    ref = classes_reference_for_prompt()

    return (
        "Ты эксперт по учёту основных средств и помощник по анализу состояния активов по фотографии.\n\n"

        "Тебе передают JSON с:\n"
        "- результатами визуального классификатора;\n"
        "- вероятностями классов;\n"
        "- top-1 классом;\n"
        "- кратким контекстом из учётной системы.\n\n"

        f"{ref}\n\n"

        "ТВОЯ ЗАДАЧА:\n"
        "Сформировать КРАТКОЕ И ЧЕЛОВЕКОЧИТАЕМОЕ заключение для сотрудника, "
        "а НЕ пересказывать JSON и НЕ выводить сырые вероятности списком.\n\n"

        "СТРУКТУРА ОТВЕТА:\n"
        "1. Краткий вывод о предполагаемом состоянии объекта.\n"
        "2. Насколько уверена модель.\n"
        "3. Есть ли риски или сомнения.\n"
        "4. Что рекомендуется сделать дальше.\n\n"

        "ВАЖНО:\n"
        "- Пиши только на русском.\n"
        "- Деловой и понятный стиль.\n"
        "- 3–6 предложений.\n"
        "- Не используй JSON.\n"
        "- Не перечисляй вероятности по всем классам.\n"
        "- Не пиши технические поля вроде `top1`, `softmax`, `probabilities`, `logits`.\n"
        "- Не пиши проценты для каждого класса подряд.\n"
        "- Разрешено упомянуть только общую уверенность модели "
        "(например: «модель уверена», «оценка неуверенная», "
        "«есть признаки повреждений»).\n\n"

        "ПРАВИЛА ИНТЕРПРЕТАЦИИ:\n"
        "- Если `weights_loaded: false` или `mode: untrained_placeholder`, "
        "сообщи, что модель ещё не обучена и автоматическая оценка недоступна.\n"

        "- Если top-1 >= 0.85:\n"
        "  Используй уверенные формулировки:\n"
        "  «модель уверенно относит объект к категории ...».\n"

        "- Если top-1 от 0.65 до 0.85:\n"
        "  Используй осторожные формулировки:\n"
        "  «по фото вероятнее всего...», «обнаружены признаки...».\n"

        "- Если top-1 < 0.65:\n"
        "  НЕ делай уверенных выводов.\n"
        "  Скажи, что автоматическая оценка неоднозначна.\n"
        "  Кратко упомяни 1–2 ближайшие альтернативы словами, без таблицы вероятностей.\n"

        "- Если доминирует `unclear`:\n"
        "  Скажи, что снимок не позволяет достоверно определить состояние.\n"
        "  Порекомендуй сделать повторное фото.\n"

        "- Если top-1 = `ok`, но `damage` или `severe` имеют заметную вероятность:\n"
        "  НЕ пиши просто «исправен».\n"
        "  Укажи, что присутствуют возможные признаки повреждений "
        "  и рекомендуется ручной осмотр.\n"

        "- Если top-1 = `damage`:\n"
        "  Укажи, что замечены признаки повреждений, "
        "  но степень дефектов требует дополнительной проверки.\n"

        "- Если top-1 = `severe`:\n"
        "  Укажи, что объект визуально имеет серьёзные повреждения "
        "  и может быть непригоден к эксплуатации.\n"

        "- Никогда не путай визуальное состояние объекта "
        "с бухгалтерским статусом («списан», «на складе» и т.д.), "
        "если этого нет во входных данных.\n\n"

        "ПРИМЕР ХОРОШЕГО ОТВЕТА:\n"
        "«По фотографии объект, вероятнее всего, имеет заметные повреждения корпуса. "
        "Модель оценивает результат с умеренной уверенностью, поэтому вывод нельзя считать окончательным. "
        "Рекомендуется провести ручной осмотр и при необходимости сделать дополнительные фотографии с других ракурсов.»"
    )


def build_condition_summary_backend(aggregate: dict, dynamics: str = "") -> str:
    """
    Формирует заключение о состоянии актива на основе результатов ConvNeXt,
    без использования внешнего LLM (GigaChat).
    Следует правилам из gigachat_condition_system_prompt.
    """
    top1 = aggregate.get("top1") or {}
    predictions = aggregate.get("predictions") or []
    confidence_level = aggregate.get("confidence_level") or "none"
    damage_score = float(aggregate.get("damage_or_severe_avg_score") or 0)
    unclear_score = float(aggregate.get("unclear_avg_score") or 0)
    image_count = aggregate.get("image_count") or 0
    needs_manual_review = aggregate.get("needs_manual_review") or False

    if not top1:
        return "Модель не смогла обработать фотографии: требуется ручной осмотр или повторные снимки."

    top1_slug = top1.get("slug")
    top1_label = top1.get("label_ru") or top1_slug
    top1_score = float(top1.get("avg_score") or 0)

    # Краткий вывод о состоянии
    if top1_slug == "ok":
        if damage_score >= 0.2:
            state_summary = "Объект визуально выглядит исправным, но присутствуют возможные признаки повреждений."
        else:
            state_summary = f"Объект, вероятнее всего, {top1_label.lower()}."
    elif top1_slug == "damage":
        state_summary = "Замечены признаки повреждений, но степень дефектов требует дополнительной проверки."
    elif top1_slug == "severe":
        state_summary = "Объект имеет серьёзные повреждения и может быть непригоден к эксплуатации."
    elif top1_slug == "unclear":
        state_summary = "Снимки не позволяют достоверно определить состояние объекта."
    else:
        state_summary = f"По фотографии объект относится к категории '{top1_label}'."

    # Уверенность модели
    if confidence_level == "high":
        confidence_summary = "Модель оценивает результат с высокой уверенностью."
    elif confidence_level == "medium":
        confidence_summary = "Модель оценивает результат с умеренной уверенностью."
    elif confidence_level == "low":
        confidence_summary = "Автоматическая оценка неоднозначна и не может считаться окончательной."
    else:
        confidence_summary = "Уверенность модели низкая."

    # Риски и сомнения
    risks = []
    if top1_slug == "ok" and damage_score >= 0.2:
        risks.append("несмотря на общий вывод, есть признаки возможных повреждений")
    if unclear_score >= 0.35:
        risks.append("снимки могут быть неинформативны")
    if confidence_level == "low":
        risks.append("низкая уверенность модели")
    if needs_manual_review:
        risks.append("рекомендуется ручная проверка")
    risk_summary = f"Есть риски: {', '.join(risks)}." if risks else "Значительных рисков не выявлено."

    # Рекомендации
    if top1_slug == "unclear" or unclear_score >= 0.35:
        recommendation = "Рекомендуется сделать повторные фотографии с других ракурсов или провести ручной осмотр."
    elif confidence_level in ("low", "medium") or needs_manual_review:
        recommendation = "Рекомендуется провести ручной осмотр для подтверждения состояния."
    else:
        recommendation = "Состояние определено автоматически, но при необходимости можно провести дополнительную проверку."

    # Согласованность снимков
    if image_count > 1:
        consistency = "Результаты между снимками согласуются." if len(predictions) == 1 or predictions[0]["top1_votes"] == image_count else "Результаты между снимками частично различаются."
    else:
        consistency = ""

    # Собрать в 3-6 предложений
    parts = [state_summary, confidence_summary]
    if consistency:
        parts.append(consistency)
    if risks:
        parts.append(risk_summary)
    parts.append(recommendation)

    return " ".join(parts[:6])  # Ограничить до 6 предложений