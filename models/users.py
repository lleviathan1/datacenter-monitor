from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models.monitoring import db


class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='operator')  # admin, operator, viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Связи
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def set_password(self, password):
        """Установка пароля с хешированием"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверка пароля"""
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission):
        """Проверка прав доступа"""
        permissions = {
            'admin': ['read', 'write', 'admin', 'delete'],
            'operator': ['read', 'write'],
            'viewer': ['read']
        }
        return permission in permissions.get(self.role, [])

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class AuditLog(db.Model):
    """Модель для аудита действий пользователей"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else 'System',
            'action': self.action,
            'resource': self.resource,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat()
        }


class SystemSettings(db.Model):
    """Модель для системных настроек"""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    category = db.Column(db.String(50), default='general')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'category': self.category,
            'updated_at': self.updated_at.isoformat()
        }


def init_default_admin():
    """Создание администратора по умолчанию"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@datacenter.local',
            role='admin'
        )
        admin.set_password('admin123')  # Временный пароль
        db.session.add(admin)

        # Добавляем стандартные системные настройки
        default_settings = [
            {
                'key': 'system_name',
                'value': 'Система мониторинга ЦОД',
                'description': 'Название системы',
                'category': 'general'
            },
            {
                'key': 'maintenance_mode',
                'value': 'false',
                'description': 'Режим обслуживания',
                'category': 'system'
            },
            {
                'key': 'backup_retention_days',
                'value': '30',
                'description': 'Срок хранения резервных копий (дни)',
                'category': 'backup'
            },
            {
                'key': 'max_login_attempts',
                'value': '5',
                'description': 'Максимальное количество попыток входа',
                'category': 'security'
            }
        ]

        for setting in default_settings:
            if not SystemSettings.query.filter_by(key=setting['key']).first():
                sys_setting = SystemSettings(**setting)
                db.session.add(sys_setting)

        try:
            db.session.commit()
            print("Создан администратор по умолчанию (admin/admin123)")
        except Exception as e:
            print(f"Ошибка создания администратора: {e}")
            db.session.rollback()