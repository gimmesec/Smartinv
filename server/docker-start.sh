#!/bin/bash
# Скрипт для запуска базы данных через Docker

echo "🚀 Запуск базы данных MySQL через Docker..."

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден!"
    echo "📝 Создайте файл .env на основе примера в DOCKER.md"
    exit 1
fi

# Запуск контейнера
docker-compose up -d

# Ожидание готовности БД
echo "⏳ Ожидание готовности базы данных..."
sleep 5

# Проверка статуса
if docker-compose ps | grep -q "Up"; then
    echo "✅ База данных успешно запущена!"
    echo ""
    echo "📊 Статус контейнеров:"
    docker-compose ps
    echo ""
    echo "💡 Полезные команды:"
    echo "   - Просмотр логов: docker-compose logs -f db"
    echo "   - Остановка: docker-compose down"
    echo "   - Подключение к БД: docker-compose exec db mysql -u bttrack_user -p bttrack"
else
    echo "❌ Ошибка при запуске базы данных!"
    echo "📋 Логи:"
    docker-compose logs db
    exit 1
fi
