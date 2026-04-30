import json
import logging
from pathlib import Path

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _resolve_image_relative_path(asset) -> str | None:
    """Выбираем последнее фото из истории или основное photo актива."""
    latest = asset.inventory_photos.order_by("-created_at").values_list("photo", flat=True).first()
    if latest:
        return str(latest)
    if asset.photo:
        return str(asset.photo)
    return None


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
    rel = job.source_image or _resolve_image_relative_path(asset)
    if not rel:
        job.status = Job.Status.FAILED
        job.error_message = "Нет фотографии актива для анализа."
        job.save(update_fields=["status", "error_message", "updated_at"])
        return

    job.source_image = rel
    job.status = Job.Status.VISION_RUNNING
    job.save(update_fields=["source_image", "status", "updated_at"])

    abs_path = Path(settings.MEDIA_ROOT) / rel
    try:
        vision = classify_image_file(str(abs_path))
    except Exception as exc:  # noqa: BLE001
        logger.exception("vision failed job=%s", job_id)
        job.status = Job.Status.FAILED
        job.error_message = str(exc)[:2000]
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise self.retry(exc=exc) from exc

    if vision.get("error"):
        job.vision_result = vision
        job.status = Job.Status.FAILED
        job.error_message = json.dumps(vision, ensure_ascii=False)
        job.save(update_fields=["vision_result", "status", "error_message", "updated_at"])
        return

    job.vision_result = vision
    job.status = Job.Status.VISION_DONE
    job.error_message = ""
    job.save(update_fields=["vision_result", "status", "error_message", "updated_at"])
    run_gigachat_condition_summary.delay(job_id)


@shared_task(bind=True, max_retries=2, default_retry_backoff=True)
def run_gigachat_condition_summary(self, job_id: int):
    from django.apps import apps

    from inventory.gigachat import chat_completion
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
    vision_json = json.dumps(job.vision_result, ensure_ascii=False, indent=2)[:8000]

    system = (
        "Ты помощник по учёту основных средств. Отвечай только на основе переданных JSON и текста. "
        "Не выдумывай повреждений и не приписывай активу состояние, если данных недостаточно. "
        "Если классы из ImageNet — явно скажи, что это технический зонд, а не оценка износа актива."
    )
    user = (
        f"Актив: {asset.name}, инв. № {asset.inventory_number}.\n\n"
        f"Динамика и контекст:\n{dynamics}\n\n"
        f"Результат визуального классификатора (JSON):\n{vision_json}\n\n"
        "Кратко (3–6 предложений на русском): что можно сказать о внешнем виде по этим данным и насколько им можно доверять."
    )
    try:
        summary = chat_completion(user, system)
    except Exception as exc:  # noqa: BLE001
        logger.exception("gigachat failed job=%s", job_id)
        job.status = Job.Status.FAILED
        job.error_message = str(exc)[:2000]
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise self.retry(exc=exc) from exc

    job.llm_summary = summary
    job.status = Job.Status.COMPLETED
    job.error_message = ""
    job.save(update_fields=["llm_summary", "status", "error_message", "updated_at"])
