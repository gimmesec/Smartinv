import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Asset, Employee, InventoryItem, InventorySession, LegalEntity, Location, OneCExchangeLog, WriteOffAct

User = get_user_model()


def _safe_attr(node: ET.Element, key: str) -> str:
    return (node.attrib.get(key) or "").strip()


def _parse_iso_datetime(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _ensure_legal_entity(external_id: str, name: str = "", tax_id: str = "") -> LegalEntity:
    external_id = (external_id or "").strip()
    name = (name or "").strip() or f"Юрлицо {external_id or 'unknown'}"
    tax_id = (tax_id or "").strip() or (external_id or f"tmp-{uuid4().hex[:10]}")
    legal_entity, _ = LegalEntity.objects.get_or_create(
        external_1c_id=external_id,
        defaults={"name": name, "tax_id": tax_id},
    )
    return legal_entity


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
        sessions_count = 0
        items_count = 0
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
                legal_entity = LegalEntity.objects.filter(external_1c_id=entity_external_id).first() or _ensure_legal_entity(
                    entity_external_id
                )
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
                legal_entity = LegalEntity.objects.filter(external_1c_id=entity_external_id).first() or _ensure_legal_entity(
                    entity_external_id
                )
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
                legal_entity = LegalEntity.objects.filter(external_1c_id=entity_external_id).first() or _ensure_legal_entity(
                    entity_external_id
                )
                employee_external_id = _safe_attr(node, "employee_id")
                location_external_id = _safe_attr(node, "location_id")
                responsible_employee = None
                location = None
                if employee_external_id:
                    responsible_employee, _ = Employee.objects.get_or_create(
                        external_1c_id=employee_external_id,
                        defaults={
                            "legal_entity": legal_entity,
                            "full_name": f"Сотрудник {employee_external_id}",
                        },
                    )
                if location_external_id:
                    location, _ = Location.objects.get_or_create(
                        external_1c_id=location_external_id,
                        defaults={
                            "legal_entity": legal_entity,
                            "name": f"Локация {location_external_id}",
                            "type": Location.LocationType.ROOM,
                        },
                    )
                Asset.objects.update_or_create(
                    external_1c_id=_safe_attr(node, "id"),
                    defaults={
                        "name": _safe_attr(node, "name") or "Без названия",
                        "inventory_number": _safe_attr(node, "inventory_number")
                        or f"inv-{uuid4().hex[:10]}",
                        "serial_number": _safe_attr(node, "serial_number"),
                        "legal_entity": legal_entity,
                        "status": _safe_attr(node, "status") or Asset.AssetStatus.ACTIVE,
                        "quantity": _safe_attr(node, "quantity") or "1.00",
                        "unit_price": _safe_attr(node, "price") or "0.00",
                        "responsible_employee": responsible_employee,
                        "location": location,
                    },
                )
                assets_count += 1

        sessions_root = root.find("inventory_sessions")
        if sessions_root is not None:
            allowed_session_status = {c[0] for c in InventorySession.SessionStatus.choices}
            allowed_item_condition = {c[0] for c in InventoryItem.Condition.choices}
            for snode in sessions_root.findall("inventory_session"):
                external_session_id = _safe_attr(snode, "id")
                if not external_session_id:
                    continue
                le_ext = _safe_attr(snode, "legal_entity_id")
                legal_entity = LegalEntity.objects.filter(external_1c_id=le_ext).first() or _ensure_legal_entity(
                    le_ext,
                    name=_safe_attr(snode, "legal_entity_name"),
                    tax_id=_safe_attr(snode, "legal_entity_tax_id"),
                )
                location = None
                loc_ext = _safe_attr(snode, "location_id")
                if loc_ext:
                    location = Location.objects.filter(external_1c_id=loc_ext).first()
                status = _safe_attr(snode, "status") or InventorySession.SessionStatus.DRAFT
                if status not in allowed_session_status:
                    status = InventorySession.SessionStatus.IN_PROGRESS
                started_by = None
                uid = _safe_attr(snode, "started_by_user_id")
                if uid.isdigit():
                    started_by = User.objects.filter(pk=int(uid)).first()
                started_at = _parse_iso_datetime(_safe_attr(snode, "started_at"))
                finished_at = _parse_iso_datetime(_safe_attr(snode, "finished_at"))
                session_defaults: dict = {
                    "legal_entity": legal_entity,
                    "location": location,
                    "started_by": started_by,
                    "status": status,
                    "finished_at": finished_at,
                }
                if started_at:
                    session_defaults["started_at"] = started_at
                session_obj, _ = InventorySession.objects.update_or_create(
                    external_1c_id=external_session_id,
                    defaults=session_defaults,
                )
                conducted_raw = _safe_attr(snode, "conducted_by_employee_ids")
                if conducted_raw:
                    refs = [x.strip() for x in conducted_raw.split(",") if x.strip()]
                    emps: list[Employee] = []
                    for ref in refs:
                        emp = Employee.objects.filter(external_1c_id=ref).first()
                        if emp is None and ref.isdigit():
                            emp = Employee.objects.filter(pk=int(ref)).first()
                        if emp is not None:
                            emps.append(emp)
                    session_obj.conducted_by_employees.set(emps)
                items_node = snode.find("items")
                if items_node is not None:
                    for inode in items_node.findall("item"):
                        asset_ext = _safe_attr(inode, "asset_id")
                        asset = Asset.objects.filter(external_1c_id=asset_ext).first()
                        if asset is None and asset_ext.isdigit():
                            asset = Asset.objects.filter(pk=int(asset_ext)).first()
                        if asset is None:
                            continue
                        cond = _safe_attr(inode, "condition") or InventoryItem.Condition.OK
                        if cond not in allowed_item_condition:
                            cond = InventoryItem.Condition.OK
                        det = _safe_attr(inode, "detected").lower()
                        detected = det in ("true", "1", "yes")
                        scanned_at = _parse_iso_datetime(_safe_attr(inode, "scanned_at"))
                        item_defaults: dict = {
                            "condition": cond,
                            "comment": _safe_attr(inode, "comment"),
                            "detected": detected,
                        }
                        if scanned_at:
                            item_defaults["scanned_at"] = scanned_at
                        InventoryItem.objects.update_or_create(
                            session=session_obj,
                            asset=asset,
                            defaults=item_defaults,
                        )
                        items_count += 1
                sessions_count += 1

        write_off_root = root.find("write_off_acts")
        if write_off_root is not None:
            for node in write_off_root.findall("write_off_act"):
                asset = Asset.objects.filter(external_1c_id=_safe_attr(node, "asset_id")).first()
                if not asset:
                    legal_entity = LegalEntity.objects.order_by("id").first() or _ensure_legal_entity("auto-generated")
                    asset = Asset.objects.create(
                        external_1c_id=_safe_attr(node, "asset_id"),
                        legal_entity=legal_entity,
                        name=f"Актив {_safe_attr(node, 'asset_id')}",
                        inventory_number=f"AUTO-{uuid4().hex[:8]}",
                        status=Asset.AssetStatus.WRITTEN_OFF,
                    )
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
            "imported_inventory_sessions": sessions_count,
            "imported_inventory_items": items_count,
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


def _build_exchange_xml(session: InventorySession | None = None) -> str:
    root = ET.Element(
        "exchange",
        {
            "format_version": "2.0",
            "generated_at": timezone.now().isoformat(),
        },
    )
    entities_root = ET.SubElement(root, "legal_entities")
    locations_root = ET.SubElement(root, "locations")
    employees_root = ET.SubElement(root, "employees")
    assets_root = ET.SubElement(root, "assets")
    inventory_sessions_root = ET.SubElement(root, "inventory_sessions")
    write_off_root = ET.SubElement(root, "write_off_acts")

    if session:
        entities_queryset = LegalEntity.objects.filter(id=session.legal_entity_id)
        locations_queryset = Location.objects.select_related("legal_entity").filter(legal_entity_id=session.legal_entity_id)
        employees_queryset = Employee.objects.select_related("legal_entity").filter(legal_entity_id=session.legal_entity_id)
        assets_queryset = Asset.objects.select_related("legal_entity", "location", "responsible_employee").filter(
            legal_entity_id=session.legal_entity_id
        )
        sessions_queryset = (
            InventorySession.objects.select_related("legal_entity", "location", "started_by")
            .prefetch_related("conducted_by_employees")
            .filter(id=session.id)
        )
        items_queryset = InventoryItem.objects.select_related("session", "asset").filter(session_id=session.id)
        write_off_queryset = WriteOffAct.objects.select_related("asset").filter(asset__legal_entity_id=session.legal_entity_id)
    else:
        entities_queryset = LegalEntity.objects.all()
        locations_queryset = Location.objects.select_related("legal_entity").all()
        employees_queryset = Employee.objects.select_related("legal_entity").all()
        assets_queryset = Asset.objects.select_related("legal_entity", "location", "responsible_employee").all()
        sessions_queryset = InventorySession.objects.select_related("legal_entity", "location", "started_by").prefetch_related(
            "conducted_by_employees"
        )
        items_queryset = InventoryItem.objects.select_related("session", "asset").all()
        write_off_queryset = WriteOffAct.objects.select_related("asset").all()

    for entity in entities_queryset:
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

    for location in locations_queryset:
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

    for employee in employees_queryset:
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

    for asset in assets_queryset:
        ET.SubElement(
            assets_root,
            "asset",
            {
                "id": asset.external_1c_id or str(asset.id),
                "name": asset.name,
                "inventory_number": asset.inventory_number,
                "serial_number": asset.serial_number or "",
                "status": asset.status,
                "quantity": str(asset.quantity),
                "price": str(asset.unit_price),
                "legal_entity_id": asset.legal_entity.external_1c_id or str(asset.legal_entity.id),
                "legal_entity_name": asset.legal_entity.name,
                "legal_entity_tax_id": asset.legal_entity.tax_id,
                "employee_id": (
                    asset.responsible_employee.external_1c_id or str(asset.responsible_employee.id)
                    if asset.responsible_employee
                    else ""
                ),
                "location_id": asset.location.external_1c_id or str(asset.location.id) if asset.location else "",
            },
        )

    items_by_session_id: dict[int, list[InventoryItem]] = {}
    for item in items_queryset:
        items_by_session_id.setdefault(item.session_id, []).append(item)

    for inventory_session in sessions_queryset:
        session_node = ET.SubElement(
            inventory_sessions_root,
            "inventory_session",
            {
                "id": inventory_session.external_1c_id or str(inventory_session.id),
                "status": inventory_session.status,
                "legal_entity_id": inventory_session.legal_entity.external_1c_id or str(inventory_session.legal_entity.id),
                "legal_entity_name": inventory_session.legal_entity.name,
                "legal_entity_tax_id": inventory_session.legal_entity.tax_id,
                "location_id": (
                    inventory_session.location.external_1c_id or str(inventory_session.location.id)
                    if inventory_session.location
                    else ""
                ),
                "started_by_user_id": str(inventory_session.started_by_id or ""),
                "conducted_by_employee_ids": ",".join(
                    str(employee.external_1c_id or employee.id) for employee in inventory_session.conducted_by_employees.all()
                ),
                "started_at": inventory_session.started_at.isoformat() if inventory_session.started_at else "",
                "finished_at": inventory_session.finished_at.isoformat() if inventory_session.finished_at else "",
            },
        )
        items_node = ET.SubElement(session_node, "items")
        for item in items_by_session_id.get(inventory_session.id, []):
            ET.SubElement(
                items_node,
                "item",
                {
                    "id": str(item.id),
                    "asset_id": item.asset.external_1c_id or str(item.asset.id),
                    "asset_name": item.asset.name,
                    "inventory_number": item.asset.inventory_number,
                    "quantity": str(item.asset.quantity),
                    "price": str(item.asset.unit_price),
                    "condition": item.condition,
                    "comment": item.comment or "",
                    "scanned_at": item.scanned_at.isoformat() if item.scanned_at else "",
                    "detected": "true" if item.detected else "false",
                },
            )

    for act in write_off_queryset:
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

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def export_to_1c_xml() -> str:
    xml_string = _build_exchange_xml()
    OneCExchangeLog.objects.create(
        direction=OneCExchangeLog.Direction.EXPORT,
        status=OneCExchangeLog.Status.SUCCESS,
        response=xml_string,
    )
    return xml_string


def export_inventory_session_to_1c_xml(session: InventorySession) -> str:
    xml_string = _build_exchange_xml(session=session)
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
