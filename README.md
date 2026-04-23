# SmartInv

SmartInv - mobile-first система учета и инвентаризации материальных активов для малого и среднего бизнеса (офисы, гостиницы, сервисные компании), развертываемая на инфраструктуре заказчика.

## Что реализовано в этом репозитории

- Серверная часть на `Django + Django REST Framework`.
- Модели учета активов, сотрудников, локаций и операций передачи.
- Обязательная сущность `Юрлицо` (`LegalEntity`) с привязкой активов.
- Закрепление актива за сотрудником (ФИО/телефон) или за локацией (офис/помещение).
- REST API для мобильного клиента (`React Native`) и веб-админки.
- Интеграция с `1С УНФ` через XML-обмен (импорт/экспорт).
- Swagger/OpenAPI документация через `drf-spectacular`.

## Архитектура

- `server/app` - Django-проект `smartinv`.
- `server/app/inventory` - доменная логика учета:
  - юрлица;
  - иерархия локаций (здание -> этаж -> помещение);
  - категории и материальные активы;
  - сотрудники и ответственные;
  - инвентаризационные сессии и результаты сканирования;
  - передачи активов;
  - журнал интеграций с 1С.

## Ключевые доменные сущности

- `LegalEntity` - юрлица (ИНН, КПП, адрес, связь с 1С).
- `Location` - иерархия расположения активов.
- `Employee` - сотрудник (ФИО, телефон, должность, юрлицо).
- `Asset` - материальный актив (инвентарный номер, статус, QR/barcode, фото, закрепление за сотрудником или локацией).
- `InventorySession` / `InventoryItem` - процесс инвентаризации со смартфона.
- `Transfer` - передача актива между сотрудниками/локациями.
- `WriteOffAct` - процедура списания изношенных активов.
- `OneCExchangeLog` - аудит обмена с 1С.

## Интеграция с 1С УНФ (основной алгоритм)

Интеграция построена через XML-пакеты и реализована в `inventory/services.py`.

### Важно про совместимость с 1С:УНФ

Текущая реализация - это **интеграционный контракт SmartInv**, а не типовой "универсальный формат УНФ из коробки".
Чтобы обмен можно было использовать в реальной организации, в 1С:УНФ нужен простой модуль сопоставления полей (обработка/расширение), который:

- читает XML из SmartInv;
- сопоставляет поля со справочниками/документами УНФ;
- возвращает внешние идентификаторы (`external_1c_id`) в SmartInv.

Такой подход нормален для большинства российских организаций: структура УНФ у всех немного отличается (доработки, расширения, разные версии), поэтому обычно внедряется "слой маппинга", а не жесткая привязка к одной конфигурации.

### Рекомендуемая структура обмена для 1С:УНФ

Ниже минимальный состав данных, чтобы обмен был практичным для типового бизнеса (ООО/ИП, несколько офисов, материальные активы на сотрудниках и помещениях).

#### 1) Справочники (выгружаются первыми)

- `legal_entities`:
  - `id` (GUID/внешний ключ из 1С, обязателен),
  - `name` (обязательно),
  - `tax_id` ИНН (обязательно),
  - `kpp` (для юрлиц),
  - `address`.
- `locations`:
  - `id` (обязательно),
  - `name` (обязательно),
  - `type` (`office`, `building`, `floor`, `room`),
  - `legal_entity_id` (обязательно).
- `employees`:
  - `id` (обязательно),
  - `full_name` (обязательно),
  - `phone`,
  - `position`,
  - `legal_entity_id` (обязательно).

#### 2) Операционные данные

- `assets`:
  - `id` (обязательно),
  - `name` (обязательно),
  - `inventory_number` (обязательно),
  - `serial_number`,
  - `status` (`active`, `damaged`, `lost`, `written_off`),
  - `legal_entity_id` (обязательно),
  - `employee_id` или `location_id` (минимум одно из двух обязательно).
- `write_off_acts`:
  - `id`,
  - `asset_id` (обязательно),
  - `reason` (обязательно),
  - `wear_level_percent`,
  - `status`.

#### 3) Требования к обмену для продакшна

- Внешний идентификатор из 1С (`external_1c_id`) используется как master key.
- Импорт должен быть идемпотентным (`update_or_create`), без дублей при повторной загрузке.
- Порядок загрузки обязателен: `legal_entities -> locations/employees -> assets -> write_off_acts`.
- Ошибки сопоставления (нет юрлица/сотрудника/локации) логируются и попадают в журнал обмена.
- Желательно подписывать/версионировать формат XML (например, `exchange format_version="1.0"`).

### 1) Импорт из 1С (`POST /api/v1/integrations/1c/import/`)

Алгоритм:
1. 1С формирует XML-пакет со справочниками (`legal_entities`, `locations`, `employees`) и данными (`assets`, `write_off_acts`).
2. SmartInv принимает XML в теле запроса.
3. Пакет парсится и валидируется.
4. Выполняется upsert по `external_1c_id`:
   - сначала юрлица;
   - затем офисы/помещения и сотрудники;
   - затем активы (с закреплением за сотрудником/локацией);
   - затем акты списания.
5. Результат и входящий payload фиксируются в `OneCExchangeLog`.

Пример XML:

```xml
<exchange>
  <legal_entities>
    <legal_entity id="e1" name="ООО Ромашка" tax_id="7701234567" kpp="770101001" />
  </legal_entities>
  <assets>
    <asset id="a1" name="Ноутбук Lenovo" inventory_number="INV-0001" legal_entity_id="e1" status="active" />
  </assets>
</exchange>
```

### 2) Экспорт в 1С (`GET /api/v1/integrations/1c/export/`)

Алгоритм:
1. SmartInv выгружает актуальные юрлица и активы в XML.
2. Формируется единый пакет `exchange`.
3. Пакет возвращается в ответе API.
4. Факт экспорта фиксируется в `OneCExchangeLog`.

### 3) Рекомендации по прод-обмену

- Запускать обмен по расписанию (например, каждые 5-15 минут) + ручной запуск.
- Использовать внешний идентификатор из 1С как master key (`external_1c_id`).
- Делать идемпотентный импорт (повторный XML не должен ломать данные).
- Вести журнал ошибок обмена и алерты для администратора.

## REST API

Базовый префикс: `api/v1/`

Основные ресурсы:

- `legal-entities/`
- `locations/`
- `asset-categories/`
- `employees/`
- `assets/`
- `inventory-sessions/`
- `inventory-items/`
- `transfers/`
- `write-off-acts/`
- `integration-logs/` (read-only)
- `integrations/1c/import/`
- `integrations/1c/export/`
- `inventory-items/{id}/ai-analyze/`

## Swagger / OpenAPI

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/swagger/`

## Быстрый запуск через Docker

### 1. Подготовить env

```bash
cd server
cp .env.example .env
```

### 2. Поднять сервисы

```bash
docker compose up --build
```

После старта будут доступны:

- Backend API: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:8000/api/swagger/`
- Django admin: `http://localhost:8000/admin/`
- pgAdmin: `http://localhost:5050/`

### 3. Создать администратора (один раз)

```bash
docker compose exec backend python manage.py createsuperuser
```

### 4. Сгенерировать тестовые данные для API

```bash
docker compose exec backend python manage.py seed_demo_data
```

Если нужно пересоздать демо-набор с очисткой текущих данных:

```bash
docker compose exec backend python manage.py seed_demo_data --clear
```

### 5. Вход в pgAdmin и подключение к БД

- Логин/пароль pgAdmin берутся из `.env`:
  - `PGADMIN_DEFAULT_EMAIL`
  - `PGADMIN_DEFAULT_PASSWORD`
- При добавлении сервера в pgAdmin используйте:
  - Host: `db`
  - Port: `5432`
  - Database: `${POSTGRES_DB}`
  - Username: `${POSTGRES_USER}`
  - Password: `${POSTGRES_PASSWORD}`

## Локальный запуск backend (без Docker)

### 1. Установить зависимости

```bash
pip install -r server/requirements.txt
```

### 2. Настроить переменные окружения

Пример:

```bash
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=*
POSTGRES_DB=smartinv
POSTGRES_USER=smartinv
POSTGRES_PASSWORD=smartinv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 3. Применить миграции и запустить сервер

```bash
cd server/app
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Мобильное приложение (Android, React Native CLI)

Реализован MVP-клиент в папке `mobile/`:

- авторизация по JWT (`/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`);
- раздел активов;
- раздел инвентаризации (выбор сессии, сканирование QR/штрихкода, отправка результата, AI-анализ);
- role-based UI: вкладка `Админ` показывается только для `is_staff/is_superuser`.

### Запуск mobile-клиента

```bash
cd mobile
npm install
npm run start
npm run android
```

Для Android-эмулятора API backend берётся с `http://10.0.2.2:8000/api/v1`.
Перед запуском убедитесь, что backend поднят через Docker (`server/docker-compose.yml`).

## Сценарий использования в дипломном проекте

- Администратор создает юрлица, структуру помещений, сотрудников и активы.
- Сотрудники выполняют инвентаризацию в мобильном приложении:
  - сканируют QR/штрих-коды;
  - фиксируют состояние и фото;
  - OCR помогает распознать инвентарные номера.
- Передачи оборудования регистрируются в системе.
- Данные синхронизируются с 1С УНФ через XML-обмен.

## Следующий этап

Для полной production-готовности рекомендуется добавить:

- асинхронные задачи (Celery/RQ) для обмена с 1С;
- фоновые проверки целостности данных;
- unit/integration тесты для XML-синхронизации.
