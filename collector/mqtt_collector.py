#!/usr/bin/env python3
"""
MQTT Collector for WirenBoard
Subscribes to MQTT topics and stores telemetry data in PostgreSQL
"""

import os
import sys
import json
import time
import signal
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any

import paho.mqtt.client as mqtt
import psycopg2
from psycopg2 import pool

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
MQTT_HOST = os.getenv('MQTT_HOST', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
# Поддержка нескольких топиков через запятую
MQTT_TOPICS_ENV = os.getenv('MQTT_TOPICS', os.getenv('MQTT_TOPIC', '/devices/+/controls/#'))
MQTT_TOPICS = [t.strip() for t in MQTT_TOPICS_ENV.split(',') if t.strip()]

DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'gold_monitoring')
DB_USER = os.getenv('DB_USER', 'golduser')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'goldpass')

# Connection pool
db_pool: Optional[pool.SimpleConnectionPool] = None

# Metrics counters
metrics: Dict[str, int] = {
    'messages_received': 0,
    'messages_saved': 0,
    'errors': 0,
    'devices_registered': 0
}
metrics_lock = threading.Lock()

# Health check
health_status = {
    'status': 'starting',
    'last_message_time': None,
    'last_error': None,
    'started_at': None
}
health_lock = threading.Lock()

# Graceful shutdown
shutdown_event = threading.Event()
mqtt_client: Optional[mqtt.Client] = None


def update_health(status: str, error: str = None):
    """Update health check status"""
    with health_lock:
        health_status['status'] = status
        health_status['last_error'] = error
        if status == 'healthy':
            health_status['last_message_time'] = datetime.now().isoformat()


def increment_metric(name: str, value: int = 1):
    """Thread-safe metric increment"""
    with metrics_lock:
        metrics[name] = metrics.get(name, 0) + value


def get_metrics() -> Dict[str, int]:
    """Thread-safe metrics read"""
    with metrics_lock:
        return metrics.copy()


def init_db_pool():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize DB pool: {e}")
        raise


def get_device_id(device_name: str, location: str, device_type: str, mqtt_topic: str) -> Optional[int]:
    """Get or create device in database"""
    if not db_pool:
        return None

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Try to find existing device
            cur.execute("""
                SELECT id FROM devices
                WHERE name = %s AND location = %s
            """, (device_name, location))
            result = cur.fetchone()

            if result:
                return result[0]

            # Create new device
            cur.execute("""
                INSERT INTO devices (name, location, device_type, mqtt_topic)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (device_name, location, device_type, mqtt_topic))
            conn.commit()
            device_id = cur.fetchone()[0]
            logger.info(f"Registered new device: {device_name} (id={device_id})")
            increment_metric('devices_registered')
            return device_id
    except Exception as e:
        logger.error(f"Error getting/creating device: {e}")
        increment_metric('errors')
        update_health('unhealthy', str(e))
        conn.rollback()
        return None
    finally:
        db_pool.putconn(conn)


def save_telemetry(device_id: int, metric: str, value: float, quality: str = 'good'):
    """Save telemetry data to database"""
    if not db_pool or not device_id:
        return

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO telemetry (device_id, metric, value, quality)
                VALUES (%s, %s, %s, %s)
            """, (device_id, metric, value, quality))
            conn.commit()
            increment_metric('messages_saved')
            update_health('healthy')
    except Exception as e:
        logger.error(f"Error saving telemetry: {e}")
        increment_metric('errors')
        update_health('unhealthy', str(e))
        conn.rollback()
    finally:
        db_pool.putconn(conn)


def parse_wirenboard_topic(topic: str):
    """
    Parse WirenBoard MQTT topic
    Формат: /devices/{device_name}/controls/{control_name}
    Пример: /devices/wb-adc/controls/V5_0
    """
    # Убираем начальный слэш если есть
    if topic.startswith('/'):
        topic = topic[1:]

    parts = topic.split('/')

    # Пропускаем meta топики (они содержат дополнительную информацию)
    if 'meta' in parts:
        return None, None, None, None

    # Формат: devices/{device_name}/controls/{control_name}
    if len(parts) >= 4 and parts[0] == 'devices' and parts[2] == 'controls':
        device_name = parts[1]      # wb-adc, battery, power_status и т.д.
        control_name = parts[3]     # V5_0, Vbus_debug, Voltage, Current и т.д.

        # Очищаем имя устройства от лишних символов
        device_name = device_name.replace('/', '_').replace('-', '_')

        location = "wirenboard"
        device_type = "sensor"
        metric = control_name

        logger.debug(f"Parsed: device={device_name}, metric={metric}")
        return device_name, location, device_type, metric

    # Если формат не распознан
    logger.debug(f"Unknown topic format: {topic}")
    return None, None, None, None


def on_connect(client, userdata, flags, rc):
    """MQTT on_connect callback"""
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        # Subscribe to all configured topics
        for topic in MQTT_TOPICS:
            client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")
        update_health('healthy')
    else:
        logger.error(f"Failed to connect to MQTT broker, result code: {rc}")
        update_health('unhealthy', f'MQTT connection failed, rc={rc}')


def on_message(client, userdata, msg):
    """MQTT on_message callback"""
    try:
        increment_metric('messages_received')
        
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='ignore')

        logger.debug(f"Received: {topic} = {payload}")

        # Parse topic
        device_name, location, device_type, metric = parse_wirenboard_topic(topic)

        if not all([device_name, metric]):
            logger.debug(f"Skipping unparseable topic: {topic}")
            return

        # Parse value
        try:
            value = float(payload)
            quality = 'good'
        except ValueError:
            # Non-numeric value (string state like "on"/"off")
            # Сохраняем только числовые значения, строки пропускаем
            logger.debug(f"Skipping non-numeric value for {metric}: {payload}")
            return

        # Get or create device
        device_id = get_device_id(device_name, location, device_type, topic)

        if device_id:
            save_telemetry(device_id, metric, value, quality)
            logger.info(f"Saved: {device_name}.{metric} = {value}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        increment_metric('errors')
        update_health('unhealthy', str(e))


def on_disconnect(client, userdata, rc):
    """MQTT on_disconnect callback"""
    if rc != 0:
        logger.warning(f"Unexpected disconnect from MQTT broker, code: {rc}")
        update_health('unhealthy', f'Unexpected disconnect, rc={rc}')
    else:
        logger.info("Disconnected from MQTT broker")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, initiating graceful shutdown...")
    shutdown_event.set()
    if mqtt_client:
        mqtt_client.disconnect()


def print_metrics():
    """Print current metrics to log"""
    m = get_metrics()
    logger.info(f"=== Metrics ===")
    logger.info(f"  Messages received: {m.get('messages_received', 0)}")
    logger.info(f"  Messages saved: {m.get('messages_saved', 0)}")
    logger.info(f"  Devices registered: {m.get('devices_registered', 0)}")
    logger.info(f"  Errors: {m.get('errors', 0)}")
    logger.info(f"===============")


def main():
    """Main entry point"""
    global mqtt_client
    
    logger.info("Starting MQTT Collector for WirenBoard")
    logger.info(f"MQTT: {MQTT_HOST}:{MQTT_PORT}, Topics: {', '.join(MQTT_TOPICS)}")
    logger.info(f"DB: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Record start time
    with health_lock:
        health_status['started_at'] = datetime.now().isoformat()

    # Wait for database to be ready
    max_retries = 30
    for i in range(max_retries):
        if shutdown_event.is_set():
            logger.info("Shutdown requested during DB initialization")
            return
        try:
            init_db_pool()
            break
        except Exception as e:
            logger.warning(f"DB not ready, retrying ({i+1}/{max_retries}): {e}")
            time.sleep(2)
    else:
        logger.error("Could not connect to database after max retries")
        update_health('unhealthy', 'Database connection failed')
        return

    # Setup MQTT client
    mqtt_client = mqtt.Client(client_id=f"gold_collector_{int(time.time())}")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    # Connect to MQTT broker
    try:
        logger.info("Connecting to MQTT broker...")
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        
        # Use loop_start for better signal handling
        mqtt_client.loop_start()
        
        # Wait for shutdown signal
        while not shutdown_event.is_set():
            time.sleep(1)
        
        # Graceful shutdown
        logger.info("Shutting down...")
        print_metrics()
        
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        
        # Close DB connections
        if db_pool:
            db_pool.closeall()
            logger.info("Database connections closed")
        
        logger.info("Shutdown complete")
        
    except Exception as e:
        logger.error(f"MQTT connection error: {e}")
        update_health('unhealthy', str(e))
        increment_metric('errors')


if __name__ == '__main__':
    main()
