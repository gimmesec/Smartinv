import json
import logging
from pathlib import Path

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        clean = str(path or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result


def _resolve_image_relative_paths(asset) -> list[str]:
    """Возвращаем все фото AssetPhoto, с fallback на legacy Asset.photo."""
    paths = [
        str(path)
        for path in asset.inventory_photos.order_by("created_at", "id").values_list("photo", flat=True)
        if path
    ]
    if asset.photo:
        paths.append(str(asset.photo))
    return _dedupe_paths(paths)


def _resolve_image_relative_path(asset) -> str | None:
    paths = _resolve_image_relative_paths(asset)
    return paths[-1] if paths else None


def _aggregate_vision_results(image_results: list[dict]) -> dict:
    scored: dict[str, dict] = {}
    inference_count = 0
    for image in image_results:
        result = image.get("result") or {}
        predictions = result.get("predictions") or []
        if not predictions:
            continue
        inference_count += 1
        for prediction in predictions:
            slug = prediction.get("slug")
            if not slug:
                continue
            item = scored.setdefault(
                slug,
                {
                    "slug": slug,
                    "label_ru": prediction.get("label_ru", ""),
                    "score_sum": 0.0,
                    "votes": 0,
                },
            )
            score = float(prediction.get("score") or 0)
            item["score_sum"] += score
            if prediction.get("rank") == 1:
                item["votes"] += 1

    predictions = []
    for item in scored.values():
        avg_score = item["score_sum"] / inference_count if inference_count else 0.0
        predictions.append(
            {
                "slug": item["slug"],
                "label_ru": item["label_ru"],
                "avg_score": avg_score,
                "top1_votes": item["votes"],
            }
        )
    predictions.sort(key=lambda item: (item["top1_votes"], item["avg_score"]), reverse=True)
    for rank, item in enumerate(predictions, start=1):
        item["rank"] = rank
    top1 = predictions[0] if predictions else None
    damage_score = sum(
        float(item.get("avg_score") or 0)
        for item in predictions
        if item.get("slug") in {"damage", "severe"}
    )
    unclear_score = next(
        (float(item.get("avg_score") or 0) for item in predictions if item.get("slug") == "unclear"),
        0.0,
    )
    top1_score = float((top1 or {}).get("avg_score") or 0)
    confidence_level = "none"
    if top1:
        if top1_score >= 0.8:
            confidence_level = "high"
        elif top1_score >= 0.65:
            confidence_level = "medium"
        else:
            confidence_level = "low"

    needs_manual_review = bool(
        top1
        and (
            confidence_level == "low"
            or unclear_score >= 0.35
            or (top1.get("slug") == "ok" and damage_score >= 0.2)
        )
    )
    return {
        "image_count": len(image_results),
        "inference_count": inference_count,
        "predictions": predictions,
        "top1": top1,
        "confidence_level": confidence_level,
        "damage_or_severe_avg_score": damage_score,
        "unclear_avg_score": unclear_score,
        "needs_manual_review": needs_manual_review,
    }


def _build_vision_risk_summary(aggregate: dict) -> str:
    top1 = aggregate.get("top1") or {}
    predictions = aggregate.get("predictions") or []
    if not top1:
        return "ConvNeXt не дала пригодных вероятностей: нужен ручной осмотр или повторные фото."

    label = top1.get("label_ru") or top1.get("slug") or "не определено"
    score = float(top1.get("avg_score") or 0)
    confidence = aggregate.get("confidence_level") or "none"
    damage_score = float(aggregate.get("damage_or_severe_avg_score") or 0)
    unclear_score = float(aggregate.get("unclear_avg_score") or 0)
    alternatives = ", ".join(
        f"{item.get('label_ru') or item.get('slug')}: {float(item.get('avg_score') or 0):.2f}"
        for item in predictions[:3]
    )

    lines = [
        f"Агрегированный top-1: {label} ({score:.2f}), уверенность: {confidence}.",
        f"Top-3 кандидата: {alternatives or 'нет данных'}.",
    ]
    if confidence == "low":
        lines.append("Top-1 ниже 0.65: нельзя формулировать уверенный вывод по фото.")
    if top1.get("slug") == "ok" and damage_score >= 0.2:
        lines.append(
            f"Несмотря на top-1 'исправен', суммарная вероятность повреждений/сильных повреждений {damage_score:.2f}: обязательно упомяни риск повреждений."
        )
    if unclear_score >= 0.35:
        lines.append(
            f"Класс 'не определить по фото' имеет заметную вероятность {unclear_score:.2f}: нужно рекомендовать повторные фото или ручной осмотр."
        )
    return "\n".join(lines)


@shared_task(bind=True, max_retries=2, default_retry_backoff=True)
def run_vision_classification(self, job_id: int):
    from django.apps import apps

    from inventory.ml.convnext_classifier import classify_image_file

    Job = apps.get_model("inventory", "AssetConditionJob")
    Asset = apps.get_model("inventory", "Asset")
    try:
        job = Job.objects.select_related("asset").get(pk=job_id)
    except Job.DoesNotExist:
        logger.error("vision job %s not found", job_id)
        return
    asset = job.asset
    source_images = _dedupe_paths(list(job.source_images or []))
    if not source_images and job.source_image:
        source_images = _dedupe_paths([job.source_image])
    if not source_images:
        source_images = _resolve_image_relative_paths(asset)
    if not source_images:
        job.status = Job.Status.FAILED
        job.error_message = "Нет фотографий актива для анализа."
        job.save(update_fields=["status", "error_message", "updated_at"])
        return

    job.source_images = source_images
    job.source_image = source_images[0]
    job.status = Job.Status.VISION_RUNNING
    job.save(update_fields=["source_image", "source_images", "status", "updated_at"])

    image_results = []
    for rel in source_images:
        abs_path = Path(settings.MEDIA_ROOT) / rel
        try:
            vision = classify_image_file(str(abs_path))
        except Exception as exc:  # noqa: BLE001
            logger.exception("vision failed job=%s image=%s", job_id, rel)
            job.status = Job.Status.FAILED
            job.error_message = str(exc)[:2000]
            job.save(update_fields=["status", "error_message", "updated_at"])
            raise self.retry(exc=exc) from exc
        image_results.append({"source_image": rel, "result": vision})

    failed_images = [item for item in image_results if (item.get("result") or {}).get("error")]
    successful_images = [item for item in image_results if not (item.get("result") or {}).get("error")]
    vision_result = {
        "mode": "multi_image",
        "source_images": source_images,
        "image_count": len(image_results),
        "successful_image_count": len(successful_images),
        "failed_image_count": len(failed_images),
        "aggregate": _aggregate_vision_results(successful_images),
        "images": image_results,
    }
    vision_result["risk_summary"] = _build_vision_risk_summary(vision_result["aggregate"])

    if not successful_images:
        job.vision_result = vision_result
        job.status = Job.Status.FAILED
        job.error_message = json.dumps(vision_result, ensure_ascii=False)[:2000]
        job.save(update_fields=["vision_result", "status", "error_message", "updated_at"])
        return

    job.vision_result = vision_result
    job.status = Job.Status.VISION_DONE
    job.error_message = ""
    job.save(update_fields=["vision_result", "status", "error_message", "updated_at"])
    run_gigachat_condition_summary.apply_async(args=[job_id], queue="llm")


@shared_task(bind=True, max_retries=8, default_retry_backoff=True, rate_limit="6/m")
def run_gigachat_condition_summary(self, job_id: int):
    from django.apps import apps

    from inventory.gigachat import GigaChatRateLimitError, chat_completion
    from inventory.ml.condition_classes import NUM_CONDITION_CLASSES, gigachat_condition_system_prompt, build_condition_summary_backend
    from inventory.ml.convnext_classifier import build_dynamics_context

    Job = apps.get_model("inventory", "AssetConditionJob")
    try:
        job = Job.objects.select_related("asset").get(pk=job_id)
    except Job.DoesNotExist:
        logger.error("llm job %s not found", job_id)
        return

    job.status = Job.Status.LLM_RUNNING
    job.save(update_fields=["status", "updated_at"])

    asset = job.asset
    dynamics = build_dynamics_context(asset.id)
    aggregate = (job.vision_result or {}).get("aggregate") or {}

    # Вместо отправки в GigaChat, формируем summary на бэкэнде
    summary = build_condition_summary_backend(aggregate, dynamics)

    job.llm_summary = summary
    job.status = Job.Status.COMPLETED
    job.error_message = ""
    job.save(update_fields=["llm_summary", "status", "error_message", "updated_at"])
