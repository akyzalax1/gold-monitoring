# Gold Monitoring - WirenBoard MQTT Collector

Система сбора данных с WirenBoard через MQTT в базу данных PostgreSQL.

## Архитектура

```
WirenBoard → MQTT (Mosquitto) → Collector → PostgreSQL → Dashboard
```

## Компоненты

- **Mosquitto** - MQTT брокер (порт 1883)
- **PostgreSQL** - База данных (порт 5432)
- **Collector** - Python сервис для сбора данных из MQTT в БД

## Запуск

```bash
docker-compose up -d --build
```

## Проверка логов

```bash
docker-compose logs -f collector
```

## Публикация тестовых данных

WirenBoard публикует данные в формате:
```
/devices/{device_name}/controls/{metric_name}
```

Пример публикации через mosquitto_pub:
```bash
docker exec gold_mosquitto mosquitto_pub -t "/devices/wb-adc/controls/V1" -m "220.5"
docker exec gold_mosquitto mosquitto_pub -t "/devices/wb-adc/controls/V2" -m "219.8"
docker exec gold_mosquitto mosquitto_pub -t "/devices/battery/controls/Voltage" -m "24.2"
```

## Проверка данных в БД

```bash
docker exec -it gold_postgres psql -U golduser -d gold_monitoring -c "SELECT * FROM devices;"
docker exec -it gold_postgres psql -U golduser -d gold_monitoring -c "SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT 10;"
```

## Настройка WirenBoard

### Вариант 1: Правила MQTT

В веб-интерфейсе WirenBoard создайте правила для отправки данных:

1. Перейдите в **Сервис** → **Правила**
2. Создайте новое правило с триггером на изменение метрики
3. Действие: **Опубликовать в MQTT топик**
4. Топик: `/devices/{device_name}/controls/{metric_name}`

### Вариант 2: Скрипт на WirenBoard

Создайте скрипт `/etc/wb-rules/wb-to-mqtt.js`:

```javascript
defineRule('wbToMqtt', {
  asSoonAs: 'wb-*',
  then: function(cell) {
    publish('/devices/' + cell.deviceId + '/controls/' + cell.name, cell.value);
  }
});
```

## Конфигурация

Переменные окружения для collector:

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| MQTT_HOST | mosquitto | Хост MQTT брокера |
| MQTT_PORT | 1883 | Порт MQTT брокера |
| MQTT_TOPICS | /devices/+/controls/# | MQTT топики для подписки (через запятую) |
| DB_HOST | postgres | Хост базы данных |
| DB_PORT | 5432 | Порт базы данных |
| DB_NAME | gold_monitoring | Имя базы данных |
| DB_USER | golduser | Пользователь БД |
| DB_PASSWORD | goldpass | Пароль БД |

## Структура БД

### devices
- id - идентификатор
- name - имя устройства
- location - местоположение
- device_type - тип устройства
- mqtt_topic - MQTT топик
- created_at - дата создания
- responsible_id - ссылка на ответственного

### telemetry
- id - идентификатор
- device_id - ссылка на устройство
- timestamp - время измерения
- metric - имя метрики
- value - значение
- quality - качество данных

## Метрики collector

Collector ведёт внутреннюю статистику:
- **messages_received** - получено сообщений от MQTT
- **messages_saved** - успешно сохранено в БД
- **devices_registered** - зарегистрировано устройств
- **errors** - количество ошибок

Метрики выводятся в лог при graceful shutdown.

## Graceful Shutdown

Collector корректно обрабатывает сигналы завершения:
- `SIGINT` (Ctrl+C)
- `SIGTERM` (docker stop)

При завершении:
1. Выводятся итоговые метрики
2. Закрываются MQTT соединения
3. Закрываются подключения к БД
