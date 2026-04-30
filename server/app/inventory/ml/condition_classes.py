"""
Пять фиксированных классов состояния актива по фото (slug = имя папки при разметке).

Папки для обучения: см. CONDITION_TRAINING_DATA_DIR (по умолчанию рядом с проектом:
``<каталог manage.py>/training_data/asset_condition/<slug>/``).
"""

from __future__ import annotations

from typing import TypedDict


class ConditionClass(TypedDict):
    slug: str
    label_ru: str
    description_ru: str


# Порядок фиксирован: индекс = метка при обучении (0..4).
CONDITION_CLASSES: tuple[ConditionClass, ...] = (
    {
        "slug": "ok",
        "label_ru": "Исправен",
        "description_ru": "Внешний вид удовлетворительный, без заметных повреждений.",
    },
    {
        "slug": "wear",
        "label_ru": "Износ",
        "description_ru": "Нормальный износ / мелкие следы эксплуатации без существенных дефектов.",
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
    lines = ["Фиксированные классы состояния по фотографии (5 штук):"]
    for i, c in enumerate(CONDITION_CLASSES, start=1):
        lines.append(f"{i}) `{c['slug']}` — {c['label_ru']}: {c['description_ru']}")
    return "\n".join(lines)


def gigachat_condition_system_prompt() -> str:
    ref = classes_reference_for_prompt()
    return (
        "Ты эксперт по учёту основных средств. Тебе передают JSON с результатом визуального классификатора "
        f"на {NUM_CONDITION_CLASSES} классов состояния актива по фотографии, плюс краткий контекст из учёта.\n\n"
        f"{ref}\n\n"
        "Правила:\n"
        "- Пиши только на русском, 3–7 предложений, деловой тон.\n"
        "- Не придумывай фактов, которых нет во входных данных.\n"
        "- Если в JSON указано, что веса классификатора не загружены (`weights_loaded: false` или `mode: untrained_placeholder`) — "
        "честно скажи, что автоматическая оценка по фото недоступна, нужно обучить модель и подключить файл весов.\n"
        "- Если классификатор выдал вероятности по классам — кратко назови наиболее вероятный класс и степень уверенности, "
        "но подчеркни, что это модель по фото, а не юридически значимый акт осмотра.\n"
        "- Если доминирует класс `unclear` — скажи, что по снимку нельзя сделать вывод, и что нужен повторный кадр.\n"
        "- Не путай классы с бухгалтерским статусом «списан» в учётной системе, если это явно не следует из контекста."
    )
