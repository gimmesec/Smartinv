# Docker Setup для BTTrack

## Быстрый старт

### 1. Создайте файл `.env` в папке `server/`

```env
# Django Settings
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (MySQL через Docker)
DB_ENGINE=django.db.backends.mysql
DB_NAME=bttrack
DB_USER=bttrack_user
DB_PASSWORD=bttrack_password
DB_HOST=localhost
DB_PORT=3306
DB_ROOT_PASSWORD=root_password

# Static & Media
STATIC_URL=/static/
STATIC_ROOT=staticfiles
MEDIA_URL=/media/
MEDIA_ROOT=media

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 2. Запустите базу данных

```bash
cd server
docker-compose up -d
```

### 3. Проверьте статус контейнера

```bash
docker-compose ps
```

### 4. Выполните миграции

```bash
python manage.py migrate
```

### 5. Создайте суперпользователя

```bash
python manage.py createsuperuser
```

## Команды Docker

### Запуск базы данных
```bash
docker-compose up -d
```

### Остановка базы данных
```bash
docker-compose down
```

### Остановка с удалением данных
```bash
docker-compose down -v
```

### Просмотр логов
```bash
docker-compose logs -f db
```

### Подключение к MySQL через командную строку
```bash
docker-compose exec db mysql -u bttrack_user -p bttrack
```

Или через root:
```bash
docker-compose exec db mysql -u root -p
```

### Перезапуск базы данных
```bash
docker-compose restart db
```

## Структура

- `docker-compose.yml` - конфигурация Docker Compose
- `docker/mysql/init/` - SQL скрипты для инициализации БД
- `.dockerignore` - файлы, исключаемые из Docker контекста

## Настройки по умолчанию

- **База данных**: MySQL 8.0
- **Порт**: 3306
- **Имя БД**: bttrack
- **Пользователь**: bttrack_user
- **Пароль**: bttrack_password (измените в .env!)
- **Root пароль**: root_password (измените в .env!)

## Важно

⚠️ **Обязательно измените пароли в `.env` файле перед использованием в production!**

## Troubleshooting

### Проблема: Порт 3306 уже занят

Измените порт в `docker-compose.yml`:
```yaml
ports:
  - "3307:3306"  # Используйте другой порт
```

И обновите `DB_PORT` в `.env`:
```env
DB_PORT=3307
```

### Проблема: Контейнер не запускается

Проверьте логи:
```bash
docker-compose logs db
```

### Проблема: Не могу подключиться к БД

Убедитесь, что:
1. Контейнер запущен: `docker-compose ps`
2. Правильные настройки в `.env`
3. БД готова: `docker-compose exec db mysqladmin ping -h localhost -u root -p`
