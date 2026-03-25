# Настройка WirenBoard для отправки данных в MQTT

## Быстрый старт

### 1. Узнайте IP вашего компьютера

На вашем компьютере (где запущен Mosquitto):

**Windows (PowerShell):**
```powershell
ipconfig
```
Найдите IPv4 адрес вашего сетевого адаптера (например, `192.168.22.100`)

### 2. Настройте MQTT на WirenBoard

**Веб-интерфейс WirenBoard:**

1. Откройте `http://192.168.22.7` в браузере
2. **Сервис** → **Настройки MQTT**
3. Заполните:
   - **Сервер MQTT**: `<IP вашего компьютера>` (например, `192.168.22.100`)
   - **Порт**: `1883`
   - **Префикс топика**: `/devices`
   - **Логин/Пароль**: оставьте пустым
   - **Включено**: ✓

4. Нажмите **Сохранить**

### 3. Перезапустите сервисы

```bash
docker-compose down
docker-compose up -d --build
```

### 4. Проверьте подключение

**На WirenBoard (SSH):**
```bash
ssh root@192.168.22.7
systemctl status wb-mqtt-serial
journalctl -u wb-mqtt-serial -f
```

**На вашем компьютере:**
```bash
# Подписка на топики WirenBoard
docker exec gold_mosquitto mosquitto_sub -v -t "/devices/#"

# Логи collector
docker-compose logs -f collector
```

---

## Детальная настройка

### Проверка сети

Убедитесь, что WirenBoard видит ваш компьютер:

```bash
# С WirenBoard
ping 192.168.22.100  # IP вашего компьютера

# С вашего компьютера
ping 192.168.22.7    # IP WirenBoard
```

### Брандмауэр Windows

Если брандмауэр блокирует подключения:

**PowerShell (от администратора):**
```powershell
# Разрешить порт 1883
New-NetFirewallRule -DisplayName "MQTT" -Direction Inbound -LocalPort 1883 -Protocol TCP -Action Allow

# Или временно отключить брандмауэр для теста
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
```

### Конфигурация Mosquitto

Файл: `mosquitto/config/mosquitto.conf`

```conf
listener 1883 0.0.0.0
allow_anonymous true
persistence true
```

---

## Стандартные топики WirenBoard

WirenBoard публикует данные автоматически:

| Топик | Описание |
|-------|----------|
| `/devices/wb-gpio-8/controls/DO1` | Дискретный выход |
| `/devices/wb-ai/controls/AI1` | Аналоговый вход |
| `/devices/wb-mwl3/controls/Temp` | Температура |
| `/devices/wb-mwl3/controls/Hum` | Влажность |
| `/devices/wb-mwl3/controls/Press` | Давление |
| `/devices/wb-mwl3/controls/CO2` | Уровень CO2 |

---

## Проверка данных в БД

```bash
docker exec -it gold_postgres psql -U golduser -d gold_monitoring -c "
SELECT 
    d.name as устройство,
    d.location as местоположение,
    t.metric as метрика,
    t.value as значение,
    t.timestamp as время
FROM telemetry t
JOIN devices d ON t.device_id = d.id
ORDER BY t.timestamp DESC 
LIMIT 20;
"
```

---

## Решение проблем

### WirenBoard не подключается

1. Проверьте логи на WirenBoard:
   ```bash
   journalctl -u wb-mqtt-serial -f --no-pager
   ```

2. Проверьте, что Mosquitto слушает:
   ```bash
   docker-compose logs mosquitto
   ```

### Данные не сохраняются

1. Проверьте логи collector:
   ```bash
   docker-compose logs collector | tail -50
   ```

2. Проверьте подключение к БД:
   ```bash
   docker exec gold_collector ping postgres
   ```

### Сброс настроек MQTT на WirenBoard

```bash
# SSH на WirenBoard
ssh root@192.168.22.7

# Перезапуск MQTT клиента
systemctl restart wb-mqtt-serial
```

---

## Полезные команды

```bash
# Перезапуск всех сервисов
docker-compose restart

# Пересоздание контейнеров
docker-compose down && docker-compose up -d

# Логи в реальном времени
docker-compose logs -f

# Только collector
docker-compose logs -f collector

# Подписка на MQTT топики
docker exec -it gold_mosquitto mosquitto_sub -v -t "/devices/#"

# Прямое подключение к БД
docker exec -it gold_postgres psql -U golduser -d gold_monitoring
```
