# Настройка WirenBoard для работы с MQTT

## 1. Настройка MQTT на WirenBoard

### Через веб-интерфейс (рекомендуется)

1. Откройте веб-интерфейс WirenBoard: `http://192.168.22.7`
2. Перейдите в **Сервис** → **Настройки MQTT**
3. Заполните параметры:

| Параметр | Значение |
|----------|----------|
| Сервер MQTT | `192.168.22.X` (IP вашего компьютера с Mosquitto) |
| Порт | `1883` |
| Логин | *(оставьте пустым, если не используется авторизация)* |
| Пароль | *(оставьте пустым, если не используется авторизация)* |
| Использовать SSL | Нет |
| Статус подключения | **Включено** |

4. Нажмите **Сохранить**

### Через конфигурационный файл (SSH)

Подключитесь к WirenBoard по SSH и отредактируйте файл:

```bash
ssh root@192.168.22.7
nano /etc/wb-mqtt-serial.conf
```

Добавьте секцию MQTT:

```json
{
  "mqtt": {
    "host": "192.168.22.X",
    "port": 1883,
    "user": "",
    "password": "",
    "prefix": "gold/andat/wirenboard"
  }
}
```

## 2. Стандартные топик WirenBoard

WirenBoard автоматически публикует данные в формате:

```
/devices/{device_id}/controls/{control_name}
```

Примеры:
- `/devices/wb-gpio-8/controls/DO1` - дискретный выход
- `/devices/wb-ai/controls/AI1` - аналоговый вход
- `/devices/wb-mwl3/controls/Temp` - температура
- `/devices/wb-mwl3/controls/Hum` - влажность

## 3. Обновление collector для стандартных топиков

Collector уже поддерживает стандартный формат WirenBoard. 
Топик для подписки: `/devices/+/controls/+`

## 4. Проверка подключения

### На WirenBoard (через SSH):

```bash
# Проверка статуса MQTT
systemctl status wb-mqtt-serial

# Логи MQTT
journalctl -u wb-mqtt-serial -f

# Тест публикации
mosquitto_pub -h 192.168.22.X -t "test/topic" -m "hello"
```

### На вашем компьютере:

```bash
# Подписка на все топики для проверки
docker exec gold_mosquitto mosquitto_sub -v -t "/devices/#"

# Проверка логов collector
docker-compose logs -f collector
```

## 5. Проверка данных в БД

```bash
docker exec -it gold_postgres psql -U golduser -d gold_monitoring -c "
SELECT 
    d.name as device,
    t.metric,
    t.value,
    t.timestamp
FROM telemetry t
JOIN devices d ON t.device_id = d.id
ORDER BY t.timestamp DESC 
LIMIT 20;
"
```

## 6. Решение проблем

### WirenBoard не подключается к MQTT

1. Проверьте сеть между WirenBoard и вашим компьютером:
   ```bash
   ping 192.168.22.7
   ```

2. Проверьте, что Mosquitto слушает правильный интерфейс:
   ```bash
   docker-compose logs mosquitto
   ```

3. Временно отключите брандмауэр для теста:
   ```bash
   # Windows (PowerShell от администратора)
   netsh advfirewall set allprofiles state off
   ```

### Данные не сохраняются в БД

1. Проверьте логи collector:
   ```bash
   docker-compose logs collector
   ```

2. Проверьте подключение к БД:
   ```bash
   docker exec -it gold_postgres psql -U golduser -d gold_monitoring -c "SELECT 1;"
   ```

## 7. Рекомендуемая структура топиков

Для надёжной архитектуры рекомендуем использовать стандартные топики WirenBoard:

```
/devices/{device_name}/controls/{metric_name}
```

Collector автоматически:
- Создаст устройство в БД
- Сохранит телеметрию с меткой времени
- Обработает числовые и строковые значения
