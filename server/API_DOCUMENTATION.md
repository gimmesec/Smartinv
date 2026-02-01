# BTTrack API Documentation

## Swagger UI

Интерактивная документация API доступна по адресам:
- **Swagger UI**: http://localhost:8000/api/swagger/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema (JSON)**: http://localhost:8000/api/schema/

## Базовый URL
```
/api/v1/
```

## Аутентификация

### Получение токена
```
POST /api/token/
Body: {
    "username": "user",
    "password": "password"
}
Response: {
    "access": "token",
    "refresh": "token"
}
```

### Обновление токена
```
POST /api/token/refresh/
Body: {
    "refresh": "refresh_token"
}
```

### Использование токена
```
Authorization: Bearer <access_token>
```

## Endpoints

### Пользователи
- `GET /api/v1/users/` - Список пользователей
- `GET /api/v1/users/{id}/` - Детали пользователя
- `GET /api/v1/users/me/` - Текущий пользователь
- `DELETE /api/v1/users/me/` - Удалить (деактивировать) свой аккаунт
- `POST /api/v1/users/` - Создать пользователя (только админ)
- `PATCH /api/v1/users/{id}/` - Обновить пользователя (только админ)

### Объекты
- `GET /api/v1/objects/` - Список объектов
- `GET /api/v1/objects/{id}/` - Детали объекта
- `POST /api/v1/objects/` - Создать объект (только админ)
- `PATCH /api/v1/objects/{id}/` - Обновить объект (только админ)

### Инструменты
- `GET /api/v1/tools/` - Список инструментов
- `GET /api/v1/tools/{id}/` - Детали инструмента
- `POST /api/v1/tools/` - Создать инструмент (только админ)
- `PATCH /api/v1/tools/{id}/` - Обновить инструмент (только админ)

### Инвентаризации
- `GET /api/v1/inventories/` - Список инвентаризаций
- `GET /api/v1/inventories/{id}/` - Детали инвентаризации
- `POST /api/v1/inventories/` - Создать инвентаризацию (бригадир/админ)

### Передачи
- `GET /api/v1/transfers/` - Список передач
- `GET /api/v1/transfers/{id}/` - Детали передачи
- `POST /api/v1/transfers/` - Создать передачу (бригадир/админ)
- `POST /api/v1/transfers/{id}/confirm/` - Подтвердить передачу
- `POST /api/v1/transfers/{id}/reject/` - Отклонить передачу
- `POST /api/v1/transfers/{id}/complete/` - Завершить передачу

### Списания
- `GET /api/v1/writeoffs/` - Список списаний
- `GET /api/v1/writeoffs/{id}/` - Детали списания
- `POST /api/v1/writeoffs/` - Создать списание (бригадир/админ)

## Права доступа

### Администратор
- Полный доступ ко всем данным
- Может создавать, изменять и удалять любые объекты

### Бригадир
- Видит данные своей бригады и объектов, которыми управляет
- Может создавать инвентаризации, передачи и списания
- Может подтверждать/отклонять/завершать передачи

### Рабочий
- Видит только свои данные
- Видит инструменты своего объекта
- Только чтение

## Фильтрация и поиск

Все списки поддерживают:
- Фильтрацию по полям через `?field=value`
- Поиск через `?search=query`
- Сортировку через `?ordering=field` или `?ordering=-field`
- Пагинацию (20 элементов на страницу)
