from flask_mail import Mail, Message
from models.settings import NotificationSettings, AlertSettings
from models.monitoring import AlertLog
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict


class NotificationService:
    """Сервис для отправки уведомлений"""

    def __init__(self, app=None, mail=None):
        self.app = app
        self.mail = mail
        self.last_notifications = {}  # Для предотвращения спама
        self.cooldown_minutes = 5  # Минут между повторными уведомлениями

    def send_alert_email(self, alert: AlertLog, escalated: bool = False):
        """Отправка email уведомления об инциденте"""
        try:
            notification_settings = NotificationSettings.query.first()
            if not notification_settings:
                print("Настройки уведомлений не найдены")
                return False

            # Проверяем cooldown для предотвращения спама
            cooldown_key = f"{alert.alert_type}_{alert.severity}"
            now = datetime.now()

            if cooldown_key in self.last_notifications:
                last_sent = self.last_notifications[cooldown_key]
                if (now - last_sent).total_seconds() < (self.cooldown_minutes * 60):
                    return False  # Слишком рано для повторного уведомления

            # Определяем получателей
            if escalated:
                email_list = json.loads(notification_settings.admin_emails or '[]')
                subject_prefix = "[КРИТИЧНО - ЭСКАЛАЦИЯ]"
            else:
                email_list = json.loads(notification_settings.to_emails or '[]')
                subject_prefix = f"[{alert.severity.upper()}]"

            if not email_list:
                print("Список получателей пуст")
                return False

            # Формируем сообщение
            subject = f"{subject_prefix} Инцидент в ЦОД: {alert.alert_type}"

            body = f"""
Обнаружен инцидент в системе мониторинга ЦОД:

Тип: {alert.alert_type}
Уровень: {alert.severity}
Сообщение: {alert.message}
Значение: {alert.value}
Порог: {alert.threshold}
Время: {alert.timestamp}

{'⚠️ ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ВМЕШАТЕЛЬСТВО ⚠️' if escalated else ''}

Проверьте панель мониторинга для получения подробной информации.
            """

            # Отправляем email
            msg = Message(
                subject=subject,
                sender=notification_settings.from_email,
                recipients=email_list,
                body=body
            )

            self.mail.send(msg)
            self.last_notifications[cooldown_key] = now

            print(f"Email уведомление отправлено: {subject}")
            return True

        except Exception as e:
            print(f"Ошибка отправки email: {e}")
            return False

    def check_escalation(self):
        """Проверка инцидентов для эскалации"""
        try:
            # Получаем настройки эскалации
            alert_settings = {s.metric_type: s for s in AlertSettings.query.all()}

            # Ищем неразрешенные критические инциденты
            critical_alerts = AlertLog.query.filter_by(
                severity='critical',
                resolved=False
            ).all()

            for alert in critical_alerts:
                setting = alert_settings.get(alert.alert_type)
                if not setting:
                    continue

                # Проверяем время с момента создания инцидента
                time_diff = datetime.now() - alert.timestamp
                if time_diff.total_seconds() > (setting.escalation_minutes * 60):
                    # Время для эскалации истекло
                    self.send_alert_email(alert, escalated=True)

                    # Отмечаем как эскалированный (можно добавить поле в модель)
                    print(f"Эскалация инцидента: {alert.message}")

        except Exception as e:
            print(f"Ошибка проверки эскалации: {e}")

    def get_notification_stats(self) -> Dict:
        """Получение статистики уведомлений"""
        try:
            now = datetime.now()
            last_24h = now - timedelta(hours=24)

            stats = {
                'total_alerts_24h': AlertLog.query.filter(AlertLog.timestamp >= last_24h).count(),
                'critical_alerts_24h': AlertLog.query.filter(
                    AlertLog.timestamp >= last_24h,
                    AlertLog.severity == 'critical'
                ).count(),
                'resolved_alerts_24h': AlertLog.query.filter(
                    AlertLog.timestamp >= last_24h,
                    AlertLog.resolved == True
                ).count(),
                'active_alerts': AlertLog.query.filter_by(resolved=False).count()
            }

            return stats

        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {}


class AlertManager:
    """Менеджер для работы с оповещениями"""

    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service

    def process_alert(self, alert_type: str, severity: str, value: float, threshold: float, message: str):
        """Обработка нового оповещения"""
        try:
            # Создаем запись в журнале
            alert = AlertLog(
                alert_type=alert_type,
                severity=severity,
                message=message,
                value=value,
                threshold=threshold
            )

            from models.monitoring import db
            db.session.add(alert)
            db.session.commit()

            # Отправляем уведомление для критических инцидентов
            if severity == 'critical':
                self.notification_service.send_alert_email(alert)

            return alert

        except Exception as e:
            print(f"Ошибка обработки оповещения: {e}")
            return None

    def resolve_alert(self, alert_id: int):
        """Разрешение инцидента"""
        try:
            alert = AlertLog.query.get(alert_id)
            if alert:
                alert.resolved = True
                from models.monitoring import db
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"Ошибка разрешения инцидента: {e}")
            return False

    def get_active_alerts(self, limit: int = 20) -> List[Dict]:
        """Получение активных оповещений"""
        try:
            alerts = AlertLog.query.filter_by(resolved=False).order_by(AlertLog.timestamp.desc()).limit(limit).all()
            return [alert.to_dict() for alert in alerts]
        except Exception as e:
            print(f"Ошибка получения активных оповещений: {e}")
            return []