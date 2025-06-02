import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = True

    # База данных
    SQLALCHEMY_DATABASE_URI = 'sqlite:///datacenter_monitor.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Настройки мониторинга
    MONITORING_INTERVAL = 5  # секунд
    MAX_DATA_POINTS = 100  # максимум точек на графике
    DATA_RETENTION_DAYS = 30  # дней хранения данных

    # Настройки Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Пороговые значения для оповещений (будут переопределены из БД)
    CPU_WARNING_THRESHOLD = 70  # %
    CPU_CRITICAL_THRESHOLD = 90  # %
    MEMORY_WARNING_THRESHOLD = 80  # %
    MEMORY_CRITICAL_THRESHOLD = 95  # %
    DISK_WARNING_THRESHOLD = 80  # %
    DISK_CRITICAL_THRESHOLD = 95  # %

    # Новые пороги для ЦОД
    TEMPERATURE_WARNING_THRESHOLD = 40  # °C
    TEMPERATURE_CRITICAL_THRESHOLD = 50  # °C
    HUMIDITY_WARNING_THRESHOLD = 70  # %
    HUMIDITY_CRITICAL_THRESHOLD = 85  # %

    # Настройки уведомлений
    ALERT_COOLDOWN_MINUTES = 5  # минут между повторными уведомлениями
    ESCALATION_CHECK_INTERVAL = 300  # секунд (5 минут)