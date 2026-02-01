# Быстрый старт с Docker

## 1. Создайте файл `.env`

Скопируйте настройки из `DOCKER.md` или используйте:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.mysql
DB_NAME=bttrack
DB_USER=bttrack_user
DB_PASSWORD=bttrack_password
DB_HOST=localhost
DB_PORT=3306
DB_ROOT_PASSWORD=root_password

STATIC_URL=/static/
STATIC_ROOT=staticfiles
MEDIA_URL=/media/
MEDIA_ROOT=media

CORS_ALLOWED_ORIGINS=http://localhost:3000
```

## 2. Запустите базу данных

**Windows:**
```bash
docker-start.bat
```

**Linux/Mac:**
```bash
chmod +x docker-start.sh
./docker-start.sh
```

**Или вручную:**
```bash
docker-compose up -d
```

## 3. Установите зависимости

```bash
pip install -r requirements.txt
```

## 4. Выполните миграции

```bash
python manage.py migrate
```

## 5. Создайте суперпользователя

```bash
python manage.py createsuperuser
```

## 6. Запустите сервер

```bash
python manage.py runserver
```

## Готово! 🎉

- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/swagger/
- Admin: http://localhost:8000/admin/
