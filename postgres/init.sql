-- Таблица приборов
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    device_type VARCHAR(50),
    mqtt_topic VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Индексы
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry(device_id);

-- Таблица ответственных
CREATE TABLE IF NOT EXISTS responsible (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact VARCHAR(100)
);

-- Добавляем поле ответственного в devices
ALTER TABLE devices ADD COLUMN IF NOT EXISTS responsible_id INTEGER REFERENCES responsible(id);

-- Тестовый прибор
INSERT INTO devices (name, location, device_type, mqtt_topic) 
VALUES ('Wirenboard-1', 'Андат', 'контроллер', 'gold/andat/wirenboard/#')
ON CONFLICT DO NOTHING;
