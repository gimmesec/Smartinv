"""ConvNeXt-Tiny: голова на NUM_CONDITION_CLASSES, веса из CONDITION_CLASSIFIER_WEIGHTS (после обучения)."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from django.conf import settings

from inventory.ml.condition_classes import (
    CLASS_LABELS_RU,
    CLASS_SLUGS,
    CONDITION_CLASSES,
    NUM_CONDITION_CLASSES,
)

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None
_transform = None
_weights_loaded: bool = False


def _weights_path() -> Path:
    return Path(getattr(settings, "CONDITION_CLASSIFIER_WEIGHTS", "") or "").expanduser()


def _build_model():
    import torch
    from torchvision.models import ConvNeXt_Tiny_Weights, convnext_tiny

    weights = ConvNeXt_Tiny_Weights.IMAGENET1K_V1
    model = convnext_tiny(weights=weights)
    last = model.classifier[-1]
    if not hasattr(last, "in_features"):
        raise RuntimeError("Не удалось определить in_features у головы ConvNeXt.")
    in_features = int(last.in_features)
    model.classifier[-1] = torch.nn.Linear(in_features, NUM_CONDITION_CLASSES)
    return model, weights.transforms()


def _load_checkpoint_into_model(model, path: Path) -> bool:
    import torch

    if not path.is_file():
        return False
    try:
        try:
            payload = torch.load(path, map_location="cpu", weights_only=True)
        except TypeError:
            payload = torch.load(path, map_location="cpu")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Не удалось прочитать веса классификатора %s: %s", path, exc)
        return False

    state = payload.get("state_dict", payload) if isinstance(payload, dict) else payload
    try:
        model.load_state_dict(state, strict=True)
    except Exception as exc:  # noqa: BLE001
        logger.exception("state_dict не подошёл к модели (ожидается вывод train_condition_classifier): %s", exc)
        return False
    return True


def _ensure_model():
    global _model, _transform, _weights_loaded
    with _lock:
        if _model is not None:
            return
        model, transform = _build_model()
        path = _weights_path()
        loaded = _load_checkpoint_into_model(model, path)
        model.eval()
        _model = model
        _transform = transform
        _weights_loaded = loaded
        if not loaded:
            logger.warning(
                "Веса классификатора состояния не найдены или битые: %s. Запустите: python manage.py train_condition_classifier",
                path,
            )


def classify_image_file(abs_path: str) -> dict[str, Any]:
    """JSON для поля vision_result: 5 классов + вероятности (если загружены веса)."""
    import torch
    from PIL import Image

    path = Path(abs_path)
    if not path.is_file():
        return {"error": "file_not_found", "path": abs_path}

    _ensure_model()
    assert _model is not None and _transform is not None

    weights_path = str(_weights_path())
    meta = {
        "architecture": "convnext_tiny",
        "num_classes": NUM_CONDITION_CLASSES,
        "class_slugs": list(CLASS_SLUGS),
        "class_labels_ru": list(CLASS_LABELS_RU),
        "weights_path": weights_path,
        "weights_loaded": _weights_loaded,
    }

    if not _weights_loaded:
        return {
            **meta,
            "mode": "untrained_placeholder",
            "message": (
                "Файл обученных весов не найден или не подходит. "
                "Разложите фото по папкам (см. CONDITION_TRAINING_DATA_DIR) и выполните: "
                "python manage.py train_condition_classifier"
            ),
            "classes_detail": CONDITION_CLASSES,
        }

    img = Image.open(path).convert("RGB")
    tensor = _transform(img).unsqueeze(0)
    with torch.no_grad():
        logits = _model(tensor)
        probs = torch.softmax(logits, dim=1).squeeze(0)
        values, indices = torch.topk(probs, k=min(5, probs.shape[0]))
        values = values.tolist()
        indices = indices.tolist()

    predictions: list[dict[str, Any]] = []
    for rank, (score, idx) in enumerate(zip(values, indices, strict=True), start=1):
        slug = CLASS_SLUGS[int(idx)]
        predictions.append(
            {
                "rank": rank,
                "slug": slug,
                "label_ru": CLASS_LABELS_RU[int(idx)],
                "score": float(score),
            }
        )

    top1 = predictions[0] if predictions else None
    return {
        **meta,
        "mode": "inference",
        "predictions": predictions,
        "top1": top1,
        "note": "Вероятности — выход обученной головы ConvNeXt по вашим 5 классам; не заменяют акт приёмки.",
    }


def build_dynamics_context(asset_id: int) -> str:
    """Краткий текст для GigaChat: статус актива и история прошлых анализов."""
    from django.apps import apps

    Asset = apps.get_model("inventory", "Asset")
    Job = apps.get_model("inventory", "AssetConditionJob")
    try:
        asset = Asset.objects.get(pk=asset_id)
    except Asset.DoesNotExist:
        return "Актив не найден."
    lines = [
        f"Статус в учёте: {asset.get_status_display()}",
        f"Последняя инвентаризация (поле): {asset.last_inventory_at or '—'}",
    ]
    prev = (
        Job.objects.filter(asset_id=asset_id, status=Job.Status.COMPLETED)
        .order_by("-updated_at")[:5]
        .values_list("llm_summary", flat=True)
    )
    summaries = [s for s in prev if s]
    if summaries:
        lines.append("Предыдущие текстовые выводы по этому активу (кратко):")
        for i, s in enumerate(summaries, 1):
            lines.append(f"{i}. {(s or '')[:400]}")
    return "\n".join(lines)
