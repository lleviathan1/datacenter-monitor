from models.monitoring import db
from datetime import datetime


class AlertSettings(db.Model):
    """Модель для настроек оповещений"""
    __tablename__ = 'alert_settings'

    id = db.Column(db.Integer, primary_key=True)
    metric_type = db.Column(db.String(50), unique=True, nullable=False)
    warning_threshold = db.Column(db.Float, nullable=False)
    critical_threshold = db.Column(db.Float, nullable=False)
    email_enabled = db.Column(db.Boolean, default=True)
    sms_enabled = db.Column(db.Boolean, default=False)
    escalation_minutes = db.Column(db.Integer, default=15)  # минут до эскалации
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'metric_type': self.metric_type,
            'warning_threshold': self.warning_threshold,
            'critical_threshold': self.critical_threshold,
            'email_enabled': self.email_enabled,
            'sms_enabled': self.sms_enabled,
            'escalation_minutes': self.escalation_minutes,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class NotificationSettings(db.Model):
    """Модель для настроек уведомлений"""
    __tablename__ = 'notification_settings'

    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(255))
    smtp_port = db.Column(db.Integer, default=587)
    smtp_username = db.Column(db.String(255))
    smtp_password = db.Column(db.String(255))
    from_email = db.Column(db.String(255))
    to_emails = db.Column(db.Text)  # JSON список email адресов
    admin_emails = db.Column(db.Text)  # JSON список admin email адресов
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'smtp_username': self.smtp_username,
            'from_email': self.from_email,
            'to_emails': self.to_emails,
            'admin_emails': self.admin_emails,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


def init_default_settings():
    """Инициализация настроек по умолчанию"""
    default_alert_settings = [
        {'metric_type': 'cpu', 'warning_threshold': 70.0, 'critical_threshold': 90.0},
        {'metric_type': 'memory', 'warning_threshold': 80.0, 'critical_threshold': 95.0},
        {'metric_type': 'disk', 'warning_threshold': 80.0, 'critical_threshold': 95.0},
        {'metric_type': 'temperature', 'warning_threshold': 40.0, 'critical_threshold': 50.0},
        {'metric_type': 'humidity', 'warning_threshold': 70.0, 'critical_threshold': 85.0}
    ]

    for setting in default_alert_settings:
        existing = AlertSettings.query.filter_by(metric_type=setting['metric_type']).first()
        if not existing:
            alert_setting = AlertSettings(**setting)
            db.session.add(alert_setting)

    # Настройки уведомлений по умолчанию
    if not NotificationSettings.query.first():
        notification_setting = NotificationSettings(
            smtp_server='smtp.gmail.com',
            smtp_port=587,
            from_email='datacenter@company.com',
            to_emails='["admin@company.com"]',
            admin_emails='["admin@company.com"]'
        )
        db.session.add(notification_setting)

    try:
        db.session.commit()
    except Exception as e:
        print(f"Ошибка инициализации настроек: {e}")
        db.session.rollback()