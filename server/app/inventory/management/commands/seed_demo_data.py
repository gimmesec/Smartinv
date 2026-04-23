from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import (
    Asset,
    AssetCategory,
    Employee,
    InventoryItem,
    InventorySession,
    LegalEntity,
    Location,
    Transfer,
    WriteOffAct,
)


class Command(BaseCommand):
    help = "Generate demo data for SmartInv API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing inventory data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_data()

        now = timezone.now()

        categories = self._seed_categories()
        entities = self._seed_legal_entities()
        locations_map = self._seed_locations(entities)
        employees_map = self._seed_employees(entities)
        self._seed_employee_users(employees_map)
        assets = self._seed_assets(categories, entities, locations_map, employees_map, now)
        self._seed_inventory(entities, locations_map, assets, now)
        self._seed_transfers(locations_map, employees_map, assets, now)
        self._seed_write_offs(entities, assets, now)

        self.stdout.write(self.style.SUCCESS("Demo data generated successfully."))

    def _clear_data(self):
        InventoryItem.objects.all().delete()
        InventorySession.objects.all().delete()
        Transfer.objects.all().delete()
        WriteOffAct.objects.all().delete()
        Asset.objects.all().delete()
        Employee.objects.all().delete()
        Location.objects.all().delete()
        AssetCategory.objects.all().delete()
        LegalEntity.objects.all().delete()
        self.stdout.write(self.style.WARNING("Existing data cleared."))

    def _seed_categories(self):
        data = [
            ("Ноутбуки", "Персональные ноутбуки сотрудников"),
            ("Сетевое оборудование", "Роутеры, коммутаторы, точки доступа"),
            ("Мебель", "Офисная мебель"),
            ("Периферия", "Мониторы, сканеры, принтеры"),
        ]
        categories = []
        for name, description in data:
            obj, _ = AssetCategory.objects.get_or_create(name=name, defaults={"description": description})
            categories.append(obj)
        return categories

    def _seed_legal_entities(self):
        entities = [
            {
                "name": "ООО СмартИнв Сервис",
                "tax_id": "7701123456",
                "kpp": "770101001",
                "address": "г. Москва, ул. Тверская, д. 10",
                "external_1c_id": "1c-le-001",
            },
            {
                "name": "ООО СК Отель Групп",
                "tax_id": "7812123456",
                "kpp": "781201001",
                "address": "г. Санкт-Петербург, Невский пр., д. 24",
                "external_1c_id": "1c-le-002",
            },
        ]
        result = []
        for item in entities:
            obj, _ = LegalEntity.objects.get_or_create(tax_id=item["tax_id"], defaults=item)
            result.append(obj)
        return result

    def _seed_locations(self, entities):
        locations_map = {}
        for idx, entity in enumerate(entities, start=1):
            office, _ = Location.objects.get_or_create(
                legal_entity=entity,
                name=f"Офис {idx}",
                type=Location.LocationType.OFFICE,
                parent=None,
                defaults={"external_1c_id": f"1c-loc-office-{idx}"},
            )
            floor, _ = Location.objects.get_or_create(
                legal_entity=entity,
                name="Этаж 1",
                type=Location.LocationType.FLOOR,
                parent=office,
                defaults={"external_1c_id": f"1c-loc-floor-{idx}"},
            )
            room_it, _ = Location.objects.get_or_create(
                legal_entity=entity,
                name="IT кабинет",
                type=Location.LocationType.ROOM,
                parent=floor,
                defaults={"external_1c_id": f"1c-loc-room-it-{idx}"},
            )
            room_acc, _ = Location.objects.get_or_create(
                legal_entity=entity,
                name="Бухгалтерия",
                type=Location.LocationType.ROOM,
                parent=floor,
                defaults={"external_1c_id": f"1c-loc-room-acc-{idx}"},
            )
            locations_map[entity.id] = {"office": office, "floor": floor, "it": room_it, "acc": room_acc}
        return locations_map

    def _seed_employees(self, entities):
        employees_map = {}
        template = [
            ("Иванов Иван Иванович", "+79990000001", "Системный администратор"),
            ("Петрова Мария Олеговна", "+79990000002", "Бухгалтер"),
            ("Сидоров Алексей Сергеевич", "+79990000003", "Менеджер"),
        ]
        for idx, entity in enumerate(entities, start=1):
            employees = []
            for pos, (full_name, phone, position) in enumerate(template, start=1):
                employee, _ = Employee.objects.get_or_create(
                    legal_entity=entity,
                    full_name=full_name,
                    defaults={
                        "phone": phone,
                        "position": position,
                        "external_1c_id": f"1c-emp-{idx}-{pos}",
                    },
                )
                employees.append(employee)
            employees_map[entity.id] = employees
        return employees_map

    def _seed_assets(self, categories, entities, locations_map, employees_map, now):
        assets = []
        for idx, entity in enumerate(entities, start=1):
            entity_locations = locations_map[entity.id]
            entity_employees = employees_map[entity.id]
            samples = [
                {
                    "name": "Ноутбук Lenovo ThinkPad E14",
                    "inventory_number": f"INV-{idx}-0001",
                    "serial_number": f"SN-LEN-{idx}-001",
                    "category": categories[0],
                    "location": entity_locations["it"],
                    "employee": entity_employees[0],
                    "status": Asset.AssetStatus.ACTIVE,
                },
                {
                    "name": "Принтер HP LaserJet",
                    "inventory_number": f"INV-{idx}-0002",
                    "serial_number": f"SN-HP-{idx}-002",
                    "category": categories[3],
                    "location": entity_locations["acc"],
                    "employee": None,
                    "status": Asset.AssetStatus.ACTIVE,
                },
                {
                    "name": "Рабочий стол офисный",
                    "inventory_number": f"INV-{idx}-0003",
                    "serial_number": f"SN-DSK-{idx}-003",
                    "category": categories[2],
                    "location": entity_locations["acc"],
                    "employee": entity_employees[1],
                    "status": Asset.AssetStatus.DAMAGED,
                },
            ]
            for pos, sample in enumerate(samples, start=1):
                asset, _ = Asset.objects.get_or_create(
                    inventory_number=sample["inventory_number"],
                    defaults={
                        "legal_entity": entity,
                        "name": sample["name"],
                        "serial_number": sample["serial_number"],
                        "category": sample["category"],
                        "location": sample["location"],
                        "responsible_employee": sample["employee"],
                        "status": sample["status"],
                        "qr_code": f"QR-{sample['inventory_number']}",
                        "barcode": f"BC-{sample['inventory_number']}",
                        "description": "Тестовый актив для проверки API",
                        "purchase_date": (now - timedelta(days=365 * (pos + 1))).date(),
                        "last_inventory_at": now - timedelta(days=30),
                        "external_1c_id": f"1c-asset-{idx}-{pos}",
                    },
                )
                assets.append(asset)
        return assets

    def _seed_employee_users(self, employees_map):
        user_model = get_user_model()
        for employees in employees_map.values():
            if not employees:
                continue
            employee = employees[0]
            username = f"emp_{employee.id}"
            user, _ = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@smartinv.local",
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            user.set_password("employee12345")
            user.save(update_fields=["password"])
            if employee.user_id != user.id:
                employee.user = user
                employee.save(update_fields=["user", "updated_at"])

    def _seed_inventory(self, entities, locations_map, assets, now):
        for entity in entities:
            session, _ = InventorySession.objects.get_or_create(
                legal_entity=entity,
                location=locations_map[entity.id]["office"],
                status=InventorySession.SessionStatus.COMPLETED,
                defaults={"finished_at": now - timedelta(days=1)},
            )
            for asset in [a for a in assets if a.legal_entity_id == entity.id]:
                InventoryItem.objects.get_or_create(
                    session=session,
                    asset=asset,
                    defaults={
                        "detected": True,
                        "detected_inventory_number": asset.inventory_number,
                        "ocr_text": f"Asset {asset.inventory_number} recognized",
                        "condition": (
                            InventoryItem.Condition.DAMAGED
                            if asset.status == Asset.AssetStatus.DAMAGED
                            else InventoryItem.Condition.OK
                        ),
                        "ai_condition": (
                            InventoryItem.Condition.DAMAGED
                            if asset.status == Asset.AssetStatus.DAMAGED
                            else InventoryItem.Condition.OK
                        ),
                        "ai_confidence": "0.84",
                        "ai_provider": "free-heuristic-v1",
                        "ai_comment": "Тестовая ИИ-оценка состояния актива",
                        "comment": "Проверено мобильным сканированием",
                    },
                )

    def _seed_transfers(self, locations_map, employees_map, assets, now):
        for asset in assets[:2]:
            employees = employees_map[asset.legal_entity_id]
            locs = locations_map[asset.legal_entity_id]
            Transfer.objects.get_or_create(
                asset=asset,
                transfer_date=now - timedelta(days=10),
                defaults={
                    "from_employee": employees[0],
                    "to_employee": employees[2],
                    "from_location": locs["it"],
                    "to_location": locs["acc"],
                    "status": Transfer.TransferStatus.APPROVED,
                    "command_text": "Передать оборудование в бухгалтерию",
                    "external_1c_id": f"1c-transfer-{asset.id}",
                },
            )

    def _seed_write_offs(self, entities, assets, now):
        damaged_assets = [asset for asset in assets if asset.status == Asset.AssetStatus.DAMAGED]
        for asset in damaged_assets:
            WriteOffAct.objects.get_or_create(
                asset=asset,
                legal_entity=asset.legal_entity,
                reason="Износ, экономически нецелесообразный ремонт",
                defaults={
                    "wear_level_percent": 85,
                    "status": WriteOffAct.WriteOffStatus.CONFIRMED,
                    "external_1c_id": f"1c-writeoff-{asset.id}",
                    "created_at": now - timedelta(days=2),
                },
            )
