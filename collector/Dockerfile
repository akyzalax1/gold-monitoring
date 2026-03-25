FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY mqtt_collector.py .

# Run the collector
CMD ["python", "mqtt_collector.py"]
