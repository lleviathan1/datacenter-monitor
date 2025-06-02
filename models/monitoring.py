from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class SystemMetrics(db.Model):
    """Модель для хранения системных метрик"""
    __tablename__ = 'system_metrics'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now, index=True)

    # Системные метрики
    cpu_percent = db.Column(db.Float)
    memory_percent = db.Column(db.Float)
    memory_used_gb = db.Column(db.Float)
    memory_total_gb = db.Column(db.Float)
    disk_percent = db.Column(db.Float)
    disk_used_gb = db.Column(db.Float)
    disk_total_gb = db.Column(db.Float)

    # Сетевые метрики
    network_sent_mb = db.Column(db.Float)
    network_recv_mb = db.Column(db.Float)
    network_packets_sent = db.Column(db.Integer)
    network_packets_recv = db.Column(db.Integer)
    network_errors_in = db.Column(db.Integer)
    network_errors_out = db.Column(db.Integer)

    # Датчики ЦОД
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    pressure = db.Column(db.Float)

    # Дополнительные метрики
    uptime_seconds = db.Column(db.Integer)
    processes_count = db.Column(db.Integer)

    def to_dict(self):
        """Преобразование в словарь для JSON"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used_gb': self.memory_used_gb,
            'memory_total_gb': self.memory_total_gb,
            'disk_percent': self.disk_percent,
            'disk_used_gb': self.disk_used_gb,
            'disk_total_gb': self.disk_total_gb,
            'network_sent_mb': self.network_sent_mb,
            'network_recv_mb': self.network_recv_mb,
            'network_packets_sent': self.network_packets_sent,
            'network_packets_recv': self.network_packets_recv,
            'network_errors_in': self.network_errors_in,
            'network_errors_out': self.network_errors_out,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'uptime_seconds': self.uptime_seconds,
            'processes_count': self.processes_count
        }


class AlertLog(db.Model):
    """Модель для журнала оповещений"""
    __tablename__ = 'alert_log'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    alert_type = db.Column(db.String(50))  # cpu, memory, disk, temperature, etc.
    severity = db.Column(db.String(20))  # info, warning, critical
    message = db.Column(db.Text)
    value = db.Column(db.Float)
    threshold = db.Column(db.Float)
    resolved = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'resolved': self.resolved
        }