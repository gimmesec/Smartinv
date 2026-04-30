"""ConvNeXt-Tiny (ImageNet-1K) inference — технический зонд конвейера до fine-tune своих весов."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()
_model = None
_transform = None
_categories: list[str] | None = None


def _ensure_model():
    global _model, _transform, _categories
    with _lock:
        if _model is not None:
            return
        import torch
        from torchvision.models import ConvNeXt_Tiny_Weights, convnext_tiny

        weights = ConvNeXt_Tiny_Weights.IMAGENET1K_V1
        _model = convnext_tiny(weights=weights)
        _model.eval()
        _transform = weights.transforms()
        _categories = list(weights.meta["categories"])


def classify_image_file(abs_path: str) -> dict[str, Any]:
    """Возвращает JSON для поля vision_result (топ-5 ImageNet)."""
    import torch
    from PIL import Image

    path = Path(abs_path)
    if not path.is_file():
        return {"error": "file_not_found", "path": abs_path}

    _ensure_model()
    img = Image.open(path).convert("RGB")
    tensor = _transform(img).unsqueeze(0)
    with torch.no_grad():
        logits = _model(tensor)
        probs = torch.softmax(logits, dim=1)
        topk = min(5, probs.shape[1])
        values, indices = torch.topk(probs, k=topk, dim=1)
        values = values.squeeze(0).tolist()
        indices = indices.squeeze(0).tolist()
        top = [
            {"rank": i + 1, "label": _categories[j], "score": float(values[i])}
            for i, j in enumerate(indices)
        ]
    return {
        "architecture": "convnext_tiny",
        "weights": "imagenet1k_v1",
        "imagenet_top5": top,
        "note": (
            "Сейчас используется предобучение ImageNet. После обучения на своих данных "
            "замените реализацию на выгрузку своих классов состояния."
        ),
    }


def build_dynamics_context(asset_id: int) -> str:
    """Краткий текст для LLM: статус актива и история прошлых анализов."""
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
        lines.append("Предыдущие выводы модели (кратко):")
        for i, s in enumerate(summaries, 1):
            lines.append(f"{i}. {(s or '')[:400]}")
    return "\n".join(lines)
