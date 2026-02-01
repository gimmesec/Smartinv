@echo off
REM Скрипт для остановки базы данных через Docker (Windows)

echo Остановка базы данных...

docker-compose down

echo База данных остановлена!
pause
