@echo off
REM Скрипт для запуска базы данных через Docker (Windows)

echo Запуск базы данных MySQL через Docker...

REM Проверка наличия .env файла
if not exist .env (
    echo Файл .env не найден!
    echo Создайте файл .env на основе примера в DOCKER.md
    pause
    exit /b 1
)

REM Запуск контейнера
docker-compose up -d

REM Ожидание готовности БД
echo Ожидание готовности базы данных...
timeout /t 5 /nobreak >nul

REM Проверка статуса
docker-compose ps

echo.
echo База данных запущена!
echo.
echo Полезные команды:
echo    - Просмотр логов: docker-compose logs -f db
echo    - Остановка: docker-compose down
echo    - Подключение к БД: docker-compose exec db mysql -u bttrack_user -p bttrack
echo.
pause
