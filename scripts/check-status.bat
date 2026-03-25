@echo off
echo ============================================
echo   Gold Monitoring - Проверка системы
echo ============================================
echo.

echo [1] Проверка статуса контейнеров...
docker-compose ps
echo.

echo [2] Логи Mosquitto (последние 10 строк)...
docker-compose logs --tail=10 mosquitto
echo.

echo [3] Логи Collector (последние 20 строк)...
docker-compose logs --tail=20 collector
echo.

echo [4] Устройства в БД...
docker exec gold_postgres psql -U golduser -d gold_monitoring -c "SELECT id, name, location, device_type FROM devices;"
echo.

echo [5] Последняя телеметрия...
docker exec gold_postgres psql -U golduser -d gold_monitoring -c "SELECT d.name, t.metric, t.value, t.timestamp FROM telemetry t JOIN devices d ON t.device_id = d.id ORDER BY t.timestamp DESC LIMIT 10;"
echo.

echo ============================================
echo   Проверка завершена
echo ============================================
pause
