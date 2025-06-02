import json
import os
import shutil
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import current_app, request
from models.monitoring import SystemMetrics, AlertLog
from models.settings import AlertSettings, NotificationSettings
from models.users import User, AuditLog, SystemSettings, db
import sqlite3
from sqlalchemy import text


class AdminService:
    """Сервис администрирования системы"""

    def __init__(self):
        self.backup_dir = 'backups'
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def log_action(self, action: str, resource: str = None, details: str = None, user_id: int = None):
        """Логирование действий пользователей"""
        try:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                details=details,
                ip_address=request.remote_addr if request else None,
                user_agent=request.user_agent.string if request else None
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            print(f"Ошибка логирования: {e}")
            db.session.rollback()

    def export_configuration(self, user_id: int) -> Dict:
        """Экспорт конфигурации системы"""
        try:
            config = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0',
                    'exported_by': user_id
                },
                'alert_settings': [],
                'notification_settings': {},
                'system_settings': [],
                'users': []
            }

            # Экспорт настроек оповещений
            alert_settings = AlertSettings.query.all()
            config['alert_settings'] = [setting.to_dict() for setting in alert_settings]

            # Экспорт настроек уведомлений
            notification_settings = NotificationSettings.query.first()
            if notification_settings:
                config['notification_settings'] = notification_settings.to_dict()
                # Удаляем пароль из экспорта
                config['notification_settings'].pop('smtp_password', None)

            # Экспорт системных настроек
            system_settings = SystemSettings.query.all()
            config['system_settings'] = [setting.to_dict() for setting in system_settings]

            # Экспорт пользователей (без паролей)
            users = User.query.all()
            for user in users:
                user_data = user.to_dict()
                config['users'].append(user_data)

            self.log_action('export_configuration', 'system', 'Экспорт конфигурации', user_id)
            return config

        except Exception as e:
            print(f"Ошибка экспорта конфигурации: {e}")
            return {}

    def import_configuration(self, config_data: Dict, user_id: int) -> Dict:
        """Импорт конфигурации системы"""
        try:
            result = {'success': True, 'imported': [], 'errors': []}

            # Импорт настроек оповещений
            if 'alert_settings' in config_data:
                for setting_data in config_data['alert_settings']:
                    try:
                        setting = AlertSettings.query.filter_by(
                            metric_type=setting_data['metric_type']
                        ).first()

                        if setting:
                            setting.warning_threshold = setting_data['warning_threshold']
                            setting.critical_threshold = setting_data['critical_threshold']
                            setting.email_enabled = setting_data['email_enabled']
                            setting.escalation_minutes = setting_data['escalation_minutes']
                        else:
                            setting = AlertSettings(**{
                                k: v for k, v in setting_data.items()
                                if k not in ['id', 'updated_at']
                            })
                            db.session.add(setting)

                        result['imported'].append(f"Настройки оповещений: {setting_data['metric_type']}")
                    except Exception as e:
                        result['errors'].append(f"Ошибка импорта настроек оповещений: {e}")

            # Импорт системных настроек
            if 'system_settings' in config_data:
                for setting_data in config_data['system_settings']:
                    try:
                        setting = SystemSettings.query.filter_by(key=setting_data['key']).first()
                        if setting:
                            setting.value = setting_data['value']
                            setting.updated_by = user_id
                            setting.updated_at = datetime.utcnow()
                        else:
                            setting_data['updated_by'] = user_id
                            setting = SystemSettings(**{
                                k: v for k, v in setting_data.items()
                                if k not in ['id', 'updated_at']
                            })
                            db.session.add(setting)

                        result['imported'].append(f"Системная настройка: {setting_data['key']}")
                    except Exception as e:
                        result['errors'].append(f"Ошибка импорта системных настроек: {e}")

            db.session.commit()
            self.log_action('import_configuration', 'system',
                            f"Импорт конфигурации: {len(result['imported'])} элементов", user_id)

            return result

        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}

    def create_backup(self, user_id: int) -> Dict:
        """Создание резервной копии"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"datacenter_backup_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, backup_name)

            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                # Добавляем базу данных
                db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
                if os.path.exists(db_path):
                    backup_zip.write(db_path, 'database.db')

                # Добавляем конфигурацию
                config = self.export_configuration(user_id)
                config_json = json.dumps(config, indent=2, ensure_ascii=False)
                backup_zip.writestr('configuration.json', config_json)

                # Добавляем метаданные
                metadata = {
                    'created_at': datetime.now().isoformat(),
                    'created_by': user_id,
                    'version': '1.0',
                    'description': 'Автоматическая резервная копия системы мониторинга ЦОД'
                }
                backup_zip.writestr('metadata.json', json.dumps(metadata, indent=2))

            self.log_action('create_backup', 'system', f"Создана резервная копия: {backup_name}", user_id)

            return {
                'success': True,
                'backup_name': backup_name,
                'backup_path': backup_path,
                'size': os.path.getsize(backup_path)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def restore_backup(self, backup_path: str, user_id: int) -> Dict:
        """Восстановление из резервной копии"""
        try:
            if not os.path.exists(backup_path):
                return {'success': False, 'error': 'Файл резервной копии не найден'}

            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                # Проверяем структуру архива
                file_list = backup_zip.namelist()

                if 'configuration.json' in file_list:
                    # Восстанавливаем конфигурацию
                    config_data = json.loads(backup_zip.read('configuration.json').decode('utf-8'))
                    import_result = self.import_configuration(config_data, user_id)

                    if not import_result['success']:
                        return {'success': False, 'error': 'Ошибка восстановления конфигурации'}

                if 'database.db' in file_list:
                    # Предупреждение: восстановление БД требует перезапуска
                    pass

            self.log_action('restore_backup', 'system', f"Восстановление из {backup_path}", user_id)

            return {
                'success': True,
                'message': 'Резервная копия успешно восстановлена'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_system_statistics(self) -> Dict:
        """Получение статистики системы"""
        try:
            stats = {}

            # Статистика базы данных
            stats['database'] = {
                'total_metrics': SystemMetrics.query.count(),
                'total_alerts': AlertLog.query.count(),
                'active_alerts': AlertLog.query.filter_by(resolved=False).count(),
                'total_users': User.query.count(),
                'active_users': User.query.filter_by(is_active=True).count()
            }

            # Статистика за последние 24 часа
            last_24h = datetime.now() - timedelta(hours=24)
            stats['last_24h'] = {
                'metrics_collected': SystemMetrics.query.filter(SystemMetrics.timestamp >= last_24h).count(),
                'alerts_generated': AlertLog.query.filter(AlertLog.timestamp >= last_24h).count(),
                'user_logins': AuditLog.query.filter(
                    AuditLog.timestamp >= last_24h,
                    AuditLog.action == 'login'
                ).count()
            }

            # Статистика хранилища
            if current_app.config.get('SQLALCHEMY_DATABASE_URI'):
                db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                if os.path.exists(db_path):
                    stats['storage'] = {
                        'database_size': os.path.getsize(db_path),
                        'backup_count': len(
                            [f for f in os.listdir(self.backup_dir) if f.endswith('.zip')]) if os.path.exists(
                            self.backup_dir) else 0
                    }

            return stats

        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {}

    def cleanup_old_data(self, retention_days: int = 30) -> Dict:
        """Очистка старых данных"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Очистка старых метрик
            old_metrics = SystemMetrics.query.filter(SystemMetrics.timestamp < cutoff_date)
            metrics_count = old_metrics.count()
            old_metrics.delete()

            # Очистка старых логов аудита
            old_audit_logs = AuditLog.query.filter(AuditLog.timestamp < cutoff_date)
            audit_count = old_audit_logs.count()
            old_audit_logs.delete()

            # Очистка разрешенных оповещений старше 7 дней
            alert_cutoff = datetime.now() - timedelta(days=7)
            old_alerts = AlertLog.query.filter(
                AlertLog.timestamp < alert_cutoff,
                AlertLog.resolved == True
            )
            alerts_count = old_alerts.count()
            old_alerts.delete()

            db.session.commit()

            return {
                'success': True,
                'cleaned': {
                    'metrics': metrics_count,
                    'audit_logs': audit_count,
                    'resolved_alerts': alerts_count
                }
            }

        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def get_system_health(self):
        """Получение информации о здоровье системы"""
        try:
            health_checks = []
            overall_status = "healthy"

            # Проверка подключения к базе данных
            try:
                db.session.execute(text('SELECT 1'))
                db.session.commit()
                health_checks.append({
                    'name': 'База данных',
                    'status': 'OK',
                    'message': 'Подключение работает'
                })
            except Exception as e:
                health_checks.append({
                    'name': 'База данных',
                    'status': 'ERROR',
                    'message': f'Ошибка подключения: {str(e)}'
                })
                overall_status = "unhealthy"

            # Проверка количества данных
            try:
                metrics_count = SystemMetrics.query.count()
                if metrics_count > 0:
                    health_checks.append({
                        'name': 'Данные метрик',
                        'status': 'OK',
                        'message': f'Доступно {metrics_count} записей'
                    })
                else:
                    health_checks.append({
                        'name': 'Данные метрик',
                        'status': 'WARNING',
                        'message': 'Нет данных метрик'
                    })
            except Exception as e:
                health_checks.append({
                    'name': 'Данные метрик',
                    'status': 'ERROR',
                    'message': f'Ошибка получения данных: {str(e)}'
                })
                overall_status = "unhealthy"

            # Проверка пользователей
            try:
                users_count = User.query.count()
                active_users = User.query.filter_by(is_active=True).count()
                health_checks.append({
                    'name': 'Пользователи',
                    'status': 'OK',
                    'message': f'Всего: {users_count}, активных: {active_users}'
                })
            except Exception as e:
                health_checks.append({
                    'name': 'Пользователи',
                    'status': 'ERROR',
                    'message': f'Ошибка: {str(e)}'
                })
                overall_status = "unhealthy"

            # Проверка настроек оповещений
            try:
                alert_settings_count = AlertSettings.query.count()
                if alert_settings_count >= 5:  # Ожидаем настройки для 5 основных метрик
                    health_checks.append({
                        'name': 'Настройки оповещений',
                        'status': 'OK',
                        'message': f'Настроено {alert_settings_count} метрик'
                    })
                else:
                    health_checks.append({
                        'name': 'Настройки оповещений',
                        'status': 'WARNING',
                        'message': f'Настроено только {alert_settings_count} метрик'
                    })
            except Exception as e:
                health_checks.append({
                    'name': 'Настройки оповещений',
                    'status': 'ERROR',
                    'message': f'Ошибка: {str(e)}'
                })

            # Проверка дискового пространства
            try:
                import shutil
                total, used, free = shutil.disk_usage('.')
                used_percent = (used / total) * 100

                if used_percent < 80:
                    status = 'OK'
                    message = f'Свободно: {free // (1024 ** 3)} ГБ ({100 - used_percent:.1f}%)'
                elif used_percent < 90:
                    status = 'WARNING'
                    message = f'Мало места: {free // (1024 ** 3)} ГБ ({100 - used_percent:.1f}%)'
                else:
                    status = 'ERROR'
                    message = f'Критически мало места: {free // (1024 ** 3)} ГБ'
                    overall_status = "unhealthy"

                health_checks.append({
                    'name': 'Дисковое пространство',
                    'status': status,
                    'message': message
                })
            except Exception as e:
                health_checks.append({
                    'name': 'Дисковое пространство',
                    'status': 'ERROR',
                    'message': f'Ошибка проверки: {str(e)}'
                })

            # Проверка работы фоновых процессов (упрощенная)
            try:
                from datetime import datetime, timedelta
                recent_data = SystemMetrics.query.filter(
                    SystemMetrics.timestamp >= datetime.utcnow() - timedelta(minutes=5)
                ).count()

                if recent_data > 0:
                    health_checks.append({
                        'name': 'Сбор данных',
                        'status': 'OK',
                        'message': f'Получено {recent_data} записей за 5 мин'
                    })
                else:
                    # Проверяем последнюю запись
                    last_record = SystemMetrics.query.order_by(SystemMetrics.timestamp.desc()).first()
                    if last_record:
                        time_diff = datetime.utcnow() - last_record.timestamp
                        minutes_ago = int(time_diff.total_seconds() / 60)
                        health_checks.append({
                            'name': 'Сбор данных',
                            'status': 'WARNING' if minutes_ago < 30 else 'ERROR',
                            'message': f'Последние данные {minutes_ago} мин назад'
                        })
                    else:
                        health_checks.append({
                            'name': 'Сбор данных',
                            'status': 'ERROR',
                            'message': 'Нет данных в системе'
                        })
            except Exception as e:
                health_checks.append({
                    'name': 'Сбор данных',
                    'status': 'ERROR',
                    'message': f'Ошибка: {str(e)}'
                })

            return {
                'overall_status': overall_status,
                'checks': health_checks,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            return {
                'overall_status': 'error',
                'checks': [{
                    'name': 'Системная ошибка',
                    'status': 'ERROR',
                    'message': f'Общая ошибка проверки: {str(e)}'
                }],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }