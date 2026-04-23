import xml.etree.ElementTree as ET
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from .models import Asset, Employee, InventorySession, LegalEntity, Location, OneCExchangeLog, WriteOffAct


def _safe_attr(node: ET.Element, key: str) -> str:
    return (node.attrib.get(key) or "").strip()


@transaction.atomic
def import_from_1c_xml(xml_payload: str) -> dict:
    """
    Алгоритм обмена с 1С УНФ:
    1) 1С выгружает XML пакет со справочниками и активами.
    2) Пакет валидируется и парсится.
    3) Сначала синхронизируются юрлица, затем активы.
    4) Каждая запись upsert-ится по external_1c_id.
    """
    started_at = timezone.now()
    log = OneCExchangeLog.objects.create(
        direction=OneCExchangeLog.Direction.IMPORT,
        status=OneCExchangeLog.Status.SUCCESS,
        payload=xml_payload,
    )
    try:
        root = ET.fromstring(xml_payload)
        entities_count = 0
        locations_count = 0
        employees_count = 0
        assets_count = 0
        write_off_count = 0

        entities_root = root.find("legal_entities")
        if entities_root is not None:
            for node in entities_root.findall("legal_entity"):
                external_id = _safe_attr(node, "id")
                defaults = {
                    "name": _safe_attr(node, "name") or "Без названия",
                    "tax_id": _safe_attr(node, "tax_id") or external_id or f"tmp-{datetime.now().timestamp()}",
                    "kpp": _safe_attr(node, "kpp"),
                    "address": _safe_attr(node, "address"),
                }
                LegalEntity.objects.update_or_create(external_1c_id=external_id, defaults=defaults)
                entities_count += 1

        locations_root = root.find("locations")
        if locations_root is not None:
            for node in locations_root.findall("location"):
                entity_external_id = _safe_attr(node, "legal_entity_id")
                legal_entity = LegalEntity.objects.filter(external_1c_id=entity_external_id).first()
                if not legal_entity:
                    continue
                Location.objects.update_or_create(
                    external_1c_id=_safe_attr(node, "id"),
                    defaults={
                        "legal_entity": legal_entity,
                        "name": _safe_attr(node, "name") or "Без названия",
                        "type": _safe_attr(node, "type") or Location.LocationType.ROOM,
                        "parent": None,
                    },
                )
                locations_count += 1

        employees_root = root.find("employees")
        if employees_root is not None:
            for node in employees_root.findall("employee"):
                entity_external_id = _safe_attr(node, "legal_entity_id")
                legal_entity = LegalEntity.objects.filter(external_1c_id=entity_external_id).first()
                if not legal_entity:
                    continue
                Employee.objects.update_or_create(
                    external_1c_id=_safe_attr(node, "id"),
                    defaults={
                        "legal_entity": legal_entity,
                        "full_name": _safe_attr(node, "full_name") or "Без имени",
                        "phone": _safe_attr(node, "phone"),
                        "position": _safe_attr(node, "position"),
                    },
                )
                employees_count += 1

        assets_root = root.find("assets")
        if assets_root is not None:
            for node in assets_root.findall("asset"):
                entity_external_id = _safe_attr(node, "legal_entity_id")
                legal_entity = LegalEntity.objects.filter(external_1c_id=entity_external_id).first()
                if not legal_entity:
                    continue
                responsible_employee = Employee.objects.filter(external_1c_id=_safe_attr(node, "employee_id")).first()
                location = Location.objects.filter(external_1c_id=_safe_attr(node, "location_id")).first()
                Asset.objects.update_or_create(
                    external_1c_id=_safe_attr(node, "id"),
                    defaults={
                        "name": _safe_attr(node, "name") or "Без названия",
                        "inventory_number": _safe_attr(node, "inventory_number")
                        or f"inv-{uuid4().hex[:10]}",
                        "serial_number": _safe_attr(node, "serial_number"),
                        "legal_entity": legal_entity,
                        "status": _safe_attr(node, "status") or Asset.AssetStatus.ACTIVE,
                        "responsible_employee": responsible_employee,
                        "location": location,
                    },
                )
                assets_count += 1

        write_off_root = root.find("write_off_acts")
        if write_off_root is not None:
            for node in write_off_root.findall("write_off_act"):
                asset = Asset.objects.filter(external_1c_id=_safe_attr(node, "asset_id")).first()
                if not asset:
                    continue
                WriteOffAct.objects.update_or_create(
                    external_1c_id=_safe_attr(node, "id"),
                    defaults={
                        "asset": asset,
                        "legal_entity": asset.legal_entity,
                        "reason": _safe_attr(node, "reason") or "Списание из 1С",
                        "wear_level_percent": int(_safe_attr(node, "wear_level_percent") or 0),
                        "status": _safe_attr(node, "status") or WriteOffAct.WriteOffStatus.CONFIRMED,
                    },
                )
                write_off_count += 1

        response = {
            "imported_legal_entities": entities_count,
            "imported_locations": locations_count,
            "imported_employees": employees_count,
            "imported_assets": assets_count,
            "imported_write_off_acts": write_off_count,
            "finished_at": timezone.now().isoformat(),
            "duration_seconds": (timezone.now() - started_at).total_seconds(),
        }
        log.response = str(response)
        log.save(update_fields=["response"])
        return response
    except Exception as exc:
        log.status = OneCExchangeLog.Status.ERROR
        log.error_message = str(exc)
        log.save(update_fields=["status", "error_message"])
        raise


def export_to_1c_xml() -> str:
    root = ET.Element("exchange")
    entities_root = ET.SubElement(root, "legal_entities")
    locations_root = ET.SubElement(root, "locations")
    employees_root = ET.SubElement(root, "employees")
    assets_root = ET.SubElement(root, "assets")
    inventory_sessions_root = ET.SubElement(root, "inventory_sessions")
    write_off_root = ET.SubElement(root, "write_off_acts")

    for entity in LegalEntity.objects.all():
        ET.SubElement(
            entities_root,
            "legal_entity",
            {
                "id": entity.external_1c_id or str(entity.id),
                "name": entity.name,
                "tax_id": entity.tax_id,
                "kpp": entity.kpp or "",
                "address": entity.address or "",
            },
        )

    for location in Location.objects.select_related("legal_entity").all():
        ET.SubElement(
            locations_root,
            "location",
            {
                "id": location.external_1c_id or str(location.id),
                "name": location.name,
                "type": location.type,
                "legal_entity_id": location.legal_entity.external_1c_id or str(location.legal_entity.id),
            },
        )

    for employee in Employee.objects.select_related("legal_entity").all():
        ET.SubElement(
            employees_root,
            "employee",
            {
                "id": employee.external_1c_id or str(employee.id),
                "full_name": employee.full_name,
                "phone": employee.phone or "",
                "position": employee.position or "",
                "legal_entity_id": employee.legal_entity.external_1c_id or str(employee.legal_entity.id),
            },
        )

    for asset in Asset.objects.select_related("legal_entity", "location", "responsible_employee").all():
        ET.SubElement(
            assets_root,
            "asset",
            {
                "id": asset.external_1c_id or str(asset.id),
                "name": asset.name,
                "inventory_number": asset.inventory_number,
                "serial_number": asset.serial_number or "",
                "status": asset.status,
                "legal_entity_id": asset.legal_entity.external_1c_id or str(asset.legal_entity.id),
                "employee_id": (
                    asset.responsible_employee.external_1c_id or str(asset.responsible_employee.id)
                    if asset.responsible_employee
                    else ""
                ),
                "location_id": asset.location.external_1c_id or str(asset.location.id) if asset.location else "",
            },
        )

    for session in InventorySession.objects.select_related("legal_entity", "location", "started_by").prefetch_related(
        "conducted_by_employees"
    ):
        ET.SubElement(
            inventory_sessions_root,
            "inventory_session",
            {
                "id": str(session.id),
                "status": session.status,
                "legal_entity_id": session.legal_entity.external_1c_id or str(session.legal_entity.id),
                "location_id": (
                    session.location.external_1c_id or str(session.location.id)
                    if session.location
                    else ""
                ),
                "started_by_user_id": str(session.started_by_id or ""),
                "conducted_by_employee_ids": ",".join(
                    str(employee.external_1c_id or employee.id) for employee in session.conducted_by_employees.all()
                ),
                "started_at": session.started_at.isoformat() if session.started_at else "",
                "finished_at": session.finished_at.isoformat() if session.finished_at else "",
            },
        )

    for act in WriteOffAct.objects.select_related("asset").all():
        ET.SubElement(
            write_off_root,
            "write_off_act",
            {
                "id": act.external_1c_id or str(act.id),
                "asset_id": act.asset.external_1c_id or str(act.asset.id),
                "reason": act.reason,
                "wear_level_percent": str(act.wear_level_percent),
                "status": act.status,
            },
        )

    xml_string = ET.tostring(root, encoding="unicode")
    OneCExchangeLog.objects.create(
        direction=OneCExchangeLog.Direction.EXPORT,
        status=OneCExchangeLog.Status.SUCCESS,
        response=xml_string,
    )
    return xml_string


def assess_inventory_item_with_ai(item) -> dict:
    """
    Базовая бесплатная эвристика (без внешнего платного API):
    - анализирует OCR/комментарий;
    - выставляет состояние и confidence;
    - может быть заменена на полноценное CV API.
    """
    text = f"{item.ocr_text or ''} {item.comment or ''}".lower()
    damaged_words = ("скол", "трещ", "повреж", "не работает", "слом")
    absent_words = ("нет", "отсутств", "не найден")

    if any(word in text for word in absent_words):
        ai_condition = "absent"
        confidence = Decimal("0.81")
        ai_comment = "Обнаружены признаки отсутствия актива по OCR/заметке."
    elif any(word in text for word in damaged_words):
        ai_condition = "damaged"
        confidence = Decimal("0.78")
        ai_comment = "Обнаружены признаки повреждения по OCR/заметке."
    else:
        ai_condition = "ok"
        confidence = Decimal("0.73")
        ai_comment = "Явные признаки проблем не найдены, рекомендуется визуальная проверка."

    item.ai_provider = "free-heuristic-v1"
    item.ai_condition = ai_condition
    item.ai_confidence = confidence
    item.ai_comment = ai_comment
    item.save(update_fields=["ai_provider", "ai_condition", "ai_confidence", "ai_comment", "updated_at"])

    return {
        "inventory_item_id": item.id,
        "ai_provider": item.ai_provider,
        "ai_condition": item.ai_condition,
        "ai_confidence": float(item.ai_confidence or 0),
        "ai_comment": item.ai_comment,
    }
