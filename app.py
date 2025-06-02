from flask_mail import Mail
from config import Config
from collectors.system_metrics import EnhancedSystemMetricsCollector
from models.monitoring import db, SystemMetrics, AlertLog
from models.settings import AlertSettings, NotificationSettings, init_default_settings
from services.notification_service import NotificationService, AlertManager
import threading
import time
import json
from analytics.analytics_service import AnalyticsService, start_analytics_background_service
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.users import User, AuditLog, SystemSettings, init_default_admin
from services.admin_service import AdminService
from flask import Flask, render_template, jsonify, request, redirect, flash
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
db.init_app(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему'

admin_service = AdminService()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Глобальные сервисы
metrics_collector = EnhancedSystemMetricsCollector()
notification_service = NotificationService(app, mail)
alert_manager = AlertManager(notification_service)
analytics_service = AnalyticsService()
current_metrics = {}


def background_monitoring():
    """Фоновый процесс сбора метрик"""
    global current_metrics

    with app.app_context():
        print("🚀 Фоновый процесс мониторинга запущен")

        # Принудительный сбор первых данных
        try:
            current_metrics = metrics_collector.get_current_metrics()
            metrics_collector.save_to_database(current_metrics)
            print("✅ Первичные данные собраны и сохранены")
        except Exception as e:
            print(f"❌ Ошибка первичного сбора: {e}")

        while True:
            try:
                # Сбор метрик
                print("🔄 Начинаем сбор данных...")
                current_metrics = metrics_collector.get_current_metrics()
                metrics_collector.add_to_history(current_metrics)

                # Сохранение в БД
                metrics_collector.save_to_database(current_metrics)
                print(f"💾 Данные сохранены, CPU: {current_metrics.get('cpu_percent', 'N/A')}%")

                # Проверка оповещений с использованием AlertManager
                metrics_collector.check_alerts(current_metrics, alert_manager)

                # Счетчик циклов
                if hasattr(background_monitoring, 'counter'):
                    background_monitoring.counter += 1
                else:
                    background_monitoring.counter = 1

                print(f"📊 Цикл {background_monitoring.counter} завершен")

                # Пауза
                print(f"😴 Спим {app.config['MONITORING_INTERVAL']} секунд...")
                time.sleep(app.config['MONITORING_INTERVAL'])

            except Exception as e:
                print(f"❌ Ошибка в фоновом мониторинге: {e}")
                import traceback
                print(f"🔍 Детали ошибки: {traceback.format_exc()}")
                time.sleep(5)


def escalation_check():
    """Фоновый процесс проверки эскалации"""
    with app.app_context():
        while True:
            try:
                notification_service.check_escalation()
                time.sleep(app.config.get('ESCALATION_CHECK_INTERVAL', 300))
            except Exception as e:
                print(f"Ошибка проверки эскалации: {e}")
                time.sleep(60)


def cleanup_old_data():
    """Очистка старых данных"""
    with app.app_context():
        while True:
            try:
                cutoff_date = datetime.now() - timedelta(days=app.config['DATA_RETENTION_DAYS'])

                old_metrics = SystemMetrics.query.filter(SystemMetrics.timestamp < cutoff_date)
                old_alerts = AlertLog.query.filter(AlertLog.timestamp < cutoff_date)

                old_metrics.delete()
                old_alerts.delete()

                db.session.commit()
                print(f"Очищены данные старше {cutoff_date}")

            except Exception as e:
                print(f"Ошибка очистки данных: {e}")
                db.session.rollback()

            time.sleep(86400)  # Раз в день


# Создание таблиц и инициализация настроек
with app.app_context():
    db.create_all()
    init_default_settings()
    init_default_admin()
    # Создаем дополнительных пользователей
    operator = User.query.filter_by(username='operator').first()
    if not operator:
        operator = User(
            username='operator',
            email='operator@datacenter.local',
            role='operator'
        )
        operator.set_password('operator123')
        db.session.add(operator)

    viewer = User.query.filter_by(username='viewer').first()
    if not viewer:
        viewer = User(
            username='viewer',
            email='viewer@datacenter.local',
            role='viewer'
        )
        viewer.set_password('viewer123')
        db.session.add(viewer)

    try:
        db.session.commit()
    except:
        db.session.rollback()


    def init_analytics():
        """Инициализация аналитики в фоновом режиме"""

        def init_task():
            with app.app_context():
                time.sleep(10)  # Ждем накопления данных
                success = analytics_service.initialize_training()
                if success:
                    print("Аналитика инициализирована успешно")
                else:
                    print("Аналитика будет инициализирована позже")

        threading.Thread(target=init_task, daemon=True).start()


    init_analytics()

# Запуск фоновых процессов
print("🚀 Запуск фоновых служб...")

try:
    monitoring_thread = threading.Thread(target=background_monitoring, daemon=True)
    monitoring_thread.start()
    print("✅ Фоновый мониторинг запущен")
except Exception as e:
    print(f"❌ Ошибка запуска мониторинга: {e}")

try:
    escalation_thread = threading.Thread(target=escalation_check, daemon=True)
    escalation_thread.start()
    print("✅ Проверка эскалации запущена")
except Exception as e:
    print(f"❌ Ошибка запуска эскалации: {e}")

try:
    cleanup_thread = threading.Thread(target=cleanup_old_data, daemon=True)
    cleanup_thread.start()
    print("✅ Очистка данных запущена")
except Exception as e:
    print(f"❌ Ошибка запуска очистки: {e}")

try:
    start_analytics_background_service(analytics_service, app)
    print("✅ Аналитический сервис запущен")
except Exception as e:
    print(f"❌ Ошибка запуска аналитики: {e}")

print("🎯 Все фоновые службы инициализированы")


# Основные маршруты
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/admin')
@login_required
def admin():
    if not current_user.has_permission('admin'):
        flash('Недостаточно прав доступа')
        return redirect('/')
    return render_template('admin.html')


# API маршруты
@app.route('/api/metrics')
@login_required
def api_metrics():
    return jsonify(current_metrics)


@app.route('/api/history')
@login_required
def api_history():
    return jsonify(metrics_collector.get_history())


@app.route('/api/status')
@login_required
def api_status():
    if not current_metrics:
        return jsonify({'status': 'initializing'})

    status = {
        'cpu_status': metrics_collector.get_status_color('cpu', current_metrics.get('cpu_percent', 0)),
        'memory_status': metrics_collector.get_status_color('memory', current_metrics.get('memory_percent', 0)),
        'disk_status': metrics_collector.get_status_color('disk', current_metrics.get('disk_percent', 0)),
        'temperature_status': metrics_collector.get_status_color('temperature', current_metrics.get('temperature', 0)),
        'humidity_status': metrics_collector.get_status_color('humidity', current_metrics.get('humidity', 0)),
        'overall_status': 'operational',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }

    return jsonify(status)


@app.route('/api/alerts')
@login_required
def api_alerts():
    """API для получения недавних оповещений"""
    try:
        recent_alerts = AlertLog.query.order_by(AlertLog.timestamp.desc()).limit(10).all()
        return jsonify([alert.to_dict() for alert in recent_alerts])
    except Exception as e:
        return jsonify([])


@app.route('/api/alerts/active')
@login_required
def api_active_alerts():
    limit = request.args.get('limit', 10, type=int)
    return jsonify(alert_manager.get_active_alerts(limit))


@app.route('/api/alerts/stats')
@login_required
def api_alert_stats():
    return jsonify(notification_service.get_notification_stats())


@app.route('/api/alerts/resolve/<int:alert_id>', methods=['POST'])
@login_required
def api_resolve_alert(alert_id):
    if not current_user.has_permission('write'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    success = alert_manager.resolve_alert(alert_id)

    if success:
        admin_service.log_action('alert_resolved', 'alerts', f'Разрешен инцидент #{alert_id}', current_user.id)

    return jsonify({'success': success})


# Настройки API
@app.route('/api/settings/alerts')
@login_required
def api_get_alert_settings():
    settings = AlertSettings.query.all()
    return jsonify([setting.to_dict() for setting in settings])


@app.route('/api/settings/alerts', methods=['POST'])
@login_required
def api_save_alert_settings():
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    try:
        data = request.get_json()

        for setting_data in data:
            setting = AlertSettings.query.filter_by(metric_type=setting_data['metric_type']).first()
            if setting:
                setting.warning_threshold = setting_data['warning_threshold']
                setting.critical_threshold = setting_data['critical_threshold']
                setting.email_enabled = setting_data['email_enabled']
                setting.escalation_minutes = setting_data['escalation_minutes']
                setting.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        admin_service.log_action('update_settings', 'alert_settings', 'Обновлены настройки оповещений', current_user.id)
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


# API для работы с настройками по умолчанию
@app.route('/api/settings/save-defaults', methods=['POST'])
@login_required
def api_save_default_settings():
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    try:
        data = request.get_json()

        # Сохраняем настройки по умолчанию в системных настройках
        default_settings_json = json.dumps(data)

        setting = SystemSettings.query.filter_by(key='default_alert_settings').first()
        if not setting:
            setting = SystemSettings(
                key='default_alert_settings',
                value=default_settings_json,
                description='Настройки оповещений по умолчанию',
                category='defaults',
                updated_by=current_user.id
            )
            db.session.add(setting)
        else:
            setting.value = default_settings_json
            setting.updated_by = current_user.id
            setting.updated_at = datetime.utcnow()

        db.session.commit()
        admin_service.log_action('save_defaults', 'alert_settings', 'Сохранены настройки по умолчанию', current_user.id)

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/settings/get-defaults')
@login_required
def api_get_default_settings():
    if not current_user.has_permission('admin'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    try:
        setting = SystemSettings.query.filter_by(key='default_alert_settings').first()
        if setting:
            return jsonify(json.loads(setting.value))
        else:
            # Возвращаем системные умолчания
            default_settings = {
                'cpu': {'warning': 70, 'critical': 85, 'email': True, 'escalation': 15},
                'memory': {'warning': 75, 'critical': 90, 'email': True, 'escalation': 10},
                'disk': {'warning': 80, 'critical': 90, 'email': True, 'escalation': 30},
                'temperature': {'warning': 30, 'critical': 40, 'email': True, 'escalation': 5},
                'humidity': {'warning': 65, 'critical': 80, 'email': False, 'escalation': 60}
            }
            return jsonify(default_settings)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/notifications')
@login_required
def api_get_notification_settings():
    settings = NotificationSettings.query.first()
    if settings:
        data = settings.to_dict()
        # Не возвращаем пароль в API
        data.pop('smtp_password', None)
        return jsonify(data)
    return jsonify({})


@app.route('/api/settings/notifications', methods=['POST'])
@login_required
def api_save_notification_settings():
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    try:
        data = request.get_json()

        settings = NotificationSettings.query.first()
        if not settings:
            settings = NotificationSettings()
            db.session.add(settings)

        settings.smtp_server = data.get('smtp_server')
        settings.smtp_port = data.get('smtp_port', 587)
        settings.smtp_username = data.get('smtp_username')
        if data.get('smtp_password'):  # Обновляем пароль только если передан
            settings.smtp_password = data.get('smtp_password')
        settings.from_email = data.get('from_email')
        settings.to_emails = json.dumps(data.get('to_emails', []))
        settings.admin_emails = json.dumps(data.get('admin_emails', []))
        settings.updated_at = datetime.utcnow()

        db.session.commit()
        admin_service.log_action('update_settings', 'notification_settings', 'Обновлены настройки уведомлений',
                                 current_user.id)
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/test-email', methods=['POST'])
@login_required
def api_test_email():
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    try:
        from flask_mail import Message

        msg = Message(
            subject="Тестовое сообщение от системы мониторинга ЦОД",
            recipients=[current_user.email],  # Отправляем текущему пользователю
            body="Это тестовое сообщение для проверки настроек email уведомлений."
        )

        mail.send(msg)
        admin_service.log_action('test_email', 'notification_settings', 'Отправлено тестовое письмо', current_user.id)
        return jsonify({'success': True, 'message': 'Тестовое письмо отправлено'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# Аналитика API
@app.route('/api/analytics/summary')
@login_required
def api_analytics_summary():
    """API для получения сводки аналитики"""
    return jsonify(analytics_service.get_analytics_summary())


@app.route('/api/analytics/anomalies')
@login_required
def api_analytics_anomalies():
    """API для получения обнаруженных аномалий"""
    limit = request.args.get('limit', 10, type=int)
    results = analytics_service.analysis_results
    anomalies_data = results.get('anomalies', {'anomalies': [], 'scores': {}})

    # Ограничиваем количество аномалий
    if limit and limit > 0:
        limited_anomalies = anomalies_data['anomalies'][:limit] if anomalies_data['anomalies'] else []
        return jsonify({
            'anomalies': limited_anomalies,
            'scores': anomalies_data.get('scores', {})
        })

    return jsonify(anomalies_data)


@app.route('/api/analytics/trends')
@login_required
def api_analytics_trends():
    """API для получения анализа трендов"""
    results = analytics_service.analysis_results
    return jsonify(results.get('trends', {'trends': {}, 'forecasts': {}}))


@app.route('/api/analytics/correlations')
@login_required
def api_analytics_correlations():
    """API для получения корреляционного анализа"""
    try:
        results = analytics_service.analysis_results
        correlations_data = results.get('correlations', {'correlations': {}, 'insights': []})

        # Если нет корреляций, попробуем запустить анализ
        if not correlations_data.get('correlations'):
            print("🔄 Запуск корреляционного анализа...")
            analytics_service.run_analysis()
            results = analytics_service.analysis_results
            correlations_data = results.get('correlations', {'correlations': {}, 'insights': []})

        # Добавляем логирование
        print(f"📊 Отправляем корреляции: {len(correlations_data.get('correlations', {}))}")
        print(f"💡 Отправляем инсайтов: {len(correlations_data.get('insights', []))}")

        return jsonify(correlations_data)

    except Exception as e:
        print(f"❌ Ошибка API корреляций: {e}")
        return jsonify({'correlations': {}, 'insights': []})


@app.route('/api/analytics/recommendations')
@login_required
def api_analytics_recommendations():
    """API для получения рекомендаций"""
    results = analytics_service.analysis_results
    return jsonify(results.get('recommendations', []))


@app.route('/analytics')
@login_required
def analytics_dashboard():
    """Страница аналитики"""
    return render_template('analytics.html')


# API для управления пользователями
@app.route('/api/users')
@login_required
def api_get_users():
    if not current_user.has_permission('admin'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@app.route('/api/users', methods=['POST'])
@login_required
def api_create_user():
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    try:
        data = request.get_json()

        # Проверяем, что пользователь не существует
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'error': 'Пользователь уже существует'})

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'error': 'Email уже используется'})

        user = User(
            username=data['username'],
            email=data['email'],
            role=data.get('role', 'viewer'),
            is_active=data.get('is_active', True)
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        admin_service.log_action('create_user', 'user_management', f'Создан пользователь {data["username"]}',
                                 current_user.id)
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        if user.id == 1 and current_user.id != 1:
            return jsonify({'success': False, 'error': 'Нельзя редактировать системного администратора'})

        data = request.get_json()

        # Проверяем уникальность username и email
        if data.get('username') != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'success': False, 'error': 'Имя пользователя уже существует'})

        if data.get('email') != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'success': False, 'error': 'Email уже используется'})

        # Обновляем данные
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.role = data.get('role', user.role)
        user.is_active = data.get('is_active', user.is_active)

        db.session.commit()

        admin_service.log_action('update_user', 'user_management',
                                f'Обновлен пользователь {user.username}', current_user.id)

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        if user.id == 1:  # Защита системного администратора
            return jsonify({'success': False, 'error': 'Нельзя удалить системного администратора'})

        username = user.username
        db.session.delete(user)
        db.session.commit()

        admin_service.log_action('delete_user', 'user_management', f'Удален пользователь {username}', current_user.id)
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


# API для системного управления
@app.route('/api/system/backup', methods=['POST'])
@login_required
def api_create_backup():
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    result = admin_service.create_backup(current_user.id)
    return jsonify(result)


@app.route('/api/system/export-config')
@login_required
def api_export_config():
    if not current_user.has_permission('admin'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    config = admin_service.export_configuration(current_user.id)
    return jsonify(config)


@app.route('/api/system/import-config', methods=['POST'])
@login_required
def api_import_config():
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'errors': ['Недостаточно прав']})

    data = request.get_json()
    result = admin_service.import_configuration(data, current_user.id)
    return jsonify(result)


@app.route('/api/system/cleanup', methods=['POST'])
@login_required
def api_cleanup_data():
    if not current_user.has_permission('admin'):
        return jsonify({'success': False, 'error': 'Недостаточно прав'})

    data = request.get_json()
    retention_days = data.get('retention_days', 30)
    result = admin_service.cleanup_old_data(retention_days)

    if result['success']:
        admin_service.log_action('cleanup_data', 'system', f'Очистка данных старше {retention_days} дней',
                                 current_user.id)

    return jsonify(result)


@app.route('/api/system/health')
@login_required
def api_system_health():
    if not current_user.has_permission('admin'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    health = admin_service.get_system_health()
    return jsonify(health)


@app.route('/api/system/background-status')
@login_required
def api_background_status():
    """API для проверки статуса фоновых процессов"""
    if not current_user.has_permission('admin'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    try:
        # Проверяем последние данные
        last_metric = SystemMetrics.query.order_by(SystemMetrics.timestamp.desc()).first()

        print(f"🔍 Отладка API background status:")
        print(f"   Последняя запись: {last_metric.timestamp if last_metric else 'Нет данных'}")
        print(f"   Текущее время: {datetime.utcnow()}")

        if last_metric:
            current_time = datetime.utcnow()
            last_time = last_metric.timestamp

            time_diff = current_time - last_time
            seconds_ago = int(time_diff.total_seconds())

            print(f"   Разница: {seconds_ago} секунд")

            status = {
                'monitoring_active': seconds_ago < 60,
                'last_data_time': last_time.strftime('%Y-%m-%d %H:%M:%S'),
                'seconds_since_last': seconds_ago,
                'current_metrics_available': bool(current_metrics),
                'total_metrics_count': SystemMetrics.query.count(),
                'debug_current_time': current_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            status = {
                'monitoring_active': False,
                'last_data_time': None,
                'seconds_since_last': None,
                'current_metrics_available': bool(current_metrics),
                'total_metrics_count': 0
            }

        print(f"   Возвращаем статус: {status}")
        return jsonify(status)

    except Exception as e:
        print(f"❌ Ошибка API background status: {e}")
        import traceback
        print(f"🔍 Детали: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/system/statistics')
@login_required
def api_system_statistics():
    if not current_user.has_permission('admin'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    stats = admin_service.get_system_statistics()
    return jsonify(stats)


# API для аудит-логов
@app.route('/api/audit-logs')
@login_required
def api_get_audit_logs():
    if not current_user.has_permission('admin'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    paginated = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'logs': [log.to_dict() for log in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page
    })


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в систему"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=False)  # Не запоминать пользователя
            user.last_login = datetime.now()
            db.session.commit()

            admin_service.log_action('login', 'system', f'Успешный вход', user.id)

            if request.is_json:
                return jsonify({'success': True, 'redirect': '/'})
            else:
                return redirect('/')
        else:
            admin_service.log_action('login_failed', 'system', f'Неудачная попытка входа: {username}')

            if request.is_json:
                return jsonify({'success': False, 'error': 'Неверные учетные данные'})
            else:
                flash('Неверные учетные данные')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    admin_service.log_action('logout', 'system', 'Выход из системы', current_user.id)
    logout_user()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)