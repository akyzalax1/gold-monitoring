-- Таблица ответственных (должна быть создана первой)
CREATE TABLE IF NOT EXISTS responsible (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact VARCHAR(100)
);

-- Таблица приборов
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    device_type VARCHAR(50),
    mqtt_topic VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responsible_id INTEGER REFERENCES responsible(id)
);

-- Таблица телеметрии
CREATE TABLE IF NOT EXISTS telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metric VARCHAR(50),
    value DOUBLE PRECISION,
    quality VARCHAR(20) DEFAULT 'good'
);

-- Индексы для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_metric ON telemetry(metric);
CREATE INDEX IF NOT EXISTS idx_devices_name ON devices(name);

-- Тестовый прибор (для отладки)
INSERT INTO devices (name, location, device_type, mqtt_topic)
VALUES ('Wirenboard-1', 'Андат', 'контроллер', '/devices/wb-*/controls/#')
ON CONFLICT ON CONSTRAINT devices_pkey DO NOTHING;
