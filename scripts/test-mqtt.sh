#!/bin/bash
# Тестовый скрипт для публикации данных в MQTT

echo "Публикация тестовых данных..."

# Температура
docker exec gold_mosquitto mosquitto_pub -t "gold/andat/wirenboard/temperature" -m "25.5"
echo "✓ temperature: 25.5"

# Влажность
docker exec gold_mosquitto mosquitto_pub -t "gold/andat/wirenboard/humidity" -m "60.2"
echo "✓ humidity: 60.2"

# Давление
docker exec gold_mosquitto mosquitto_pub -t "gold/andat/wirenboard/pressure" -m "760"
echo "✓ pressure: 760"

# Напряжение
docker exec gold_mosquitto mosquitto_pub -t "gold/andat/wirenboard/voltage" -m "220.5"
echo "✓ voltage: 220.5"

# Ток
docker exec gold_mosquitto mosquitto_pub -t "gold/andat/wirenboard/current" -m "0.15"
echo "✓ current: 0.15"

echo ""
echo "Данные опубликованы!"
echo "Проверьте логи collector: docker-compose logs -f collector"
echo "Проверьте БД: docker exec -it gold_postgres psql -U golduser -d gold_monitoring -c \"SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT 10;\""
