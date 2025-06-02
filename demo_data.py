"""
Генератор демо-данных для системы мониторинга ЦОД
Запускать: python demo_data.py
"""

import random
import time
from datetime import datetime, timedelta
from models.monitoring import db, SystemMetrics, AlertLog
from models.users import AuditLog, User
from app import app
import math


def generate_demo_metrics(days=7, points_per_day=288):
    """Генерация демо-метрик за указанное количество дней"""
    print(f"Генерация демо-данных за {days} дней...")

    start_time = datetime.now() - timedelta(days=days)
    interval_minutes = (24 * 60) // points_per_day  # интервал в минутах

    generated_count = 0

    for day in range(days):
        day_start = start_time + timedelta(days=day)

        # Базовые значения для дня с небольшими вариациями
        base_cpu = random.uniform(20, 40)
        base_memory = random.uniform(30, 50)
        base_disk = random.uniform(40, 60)
        base_temp = random.uniform(23, 27)
        base_humidity = random.uniform(40, 60)
        base_pressure = random.uniform(1010, 1020)

        for point in range(points_per_day):
            timestamp = day_start + timedelta(minutes=point * interval_minutes)

            # Добавляем временные паттерны (рабочие часы = больше нагрузка)
            hour = timestamp.hour
            work_factor = 1.0
            if 9 <= hour <= 18:  # рабочие часы
                work_factor = 1.3
            elif 22 <= hour or hour <= 6:  # ночные часы
                work_factor = 0.7

            # Генерируем метрики с реалистичными колебаниями
            cpu_percent = base_cpu * work_factor + random.uniform(-10, 15)
            cpu_percent = max(5, min(95, cpu_percent))

            memory_percent = base_memory * work_factor + random.uniform(-8, 12)
            memory_percent = max(10, min(90, memory_percent))

            disk_percent = base_disk + random.uniform(-2, 3)
            disk_percent = max(20, min(85, disk_percent))

            # Температура коррелирует с нагрузкой CPU
            temp_factor = 1.0 + (cpu_percent - 30) * 0.01
            temperature = base_temp * temp_factor + random.uniform(-2, 3)
            temperature = max(18, min(45, temperature))

            humidity = base_humidity + random.uniform(-10, 10)
            humidity = max(30, min(80, humidity))

            pressure = base_pressure + random.uniform(-3, 3)

            # Сетевые метрики
            network_base = random.uniform(100, 1000)
            network_sent = network_base * work_factor + random.uniform(-50, 100)
            network_recv = network_base * work_factor + random.uniform(-50, 100)

            # Создаем иногда аномалии для демонстрации
            if random.random() < 0.05:  # 5% шанс аномалии
                anomaly_type = random.choice(['cpu_spike', 'memory_spike', 'temp_spike'])
                if anomaly_type == 'cpu_spike':
                    cpu_percent = min(95, cpu_percent + random.uniform(20, 40))
                elif anomaly_type == 'memory_spike':
                    memory_percent = min(95, memory_percent + random.uniform(15, 30))
                elif anomaly_type == 'temp_spike':
                    temperature = min(50, temperature + random.uniform(8, 15))

            # Создаем запись в БД
            metric = SystemMetrics(
                timestamp=timestamp,
                cpu_percent=round(cpu_percent, 1),
                memory_percent=round(memory_percent, 1),
                memory_used_gb=round(memory_percent * 16 / 100, 1),  # Предполагаем 16GB RAM
                memory_total_gb=16.0,
                disk_percent=round(disk_percent, 1),
                disk_used_gb=round(disk_percent * 500 / 100, 1),  # Предполагаем 500GB диск
                disk_total_gb=500.0,
                network_sent_mb=round(network_sent, 1),
                network_recv_mb=round(network_recv, 1),
                network_packets_sent=int(network_sent * 1000),
                network_packets_recv=int(network_recv * 1000),
                network_errors_in=random.randint(0, 5),
                network_errors_out=random.randint(0, 5),
                temperature=round(temperature, 1),
                humidity=round(humidity, 1),
                pressure=round(pressure, 1),
                uptime_seconds=int((timestamp - start_time).total_seconds()),
                processes_count=random.randint(150, 300)
            )

            db.session.add(metric)
            generated_count += 1

            # Периодически сохраняем в БД
            if generated_count % 100 == 0:
                try:
                    db.session.commit()
                    print(f"Сгенерировано {generated_count} записей...")
                except Exception as e:
                    print(f"Ошибка сохранения: {e}")
                    db.session.rollback()

    # Финальное сохранение
    try:
        db.session.commit()
        print(f"✅ Успешно сгенерировано {generated_count} записей метрик")
        return True
    except Exception as e:
        print(f"❌ Ошибка финального сохранения: {e}")
        db.session.rollback()
        return False


def generate_demo_alerts():
    """Генерация демо-оповещений"""
    print("Генерация демо-оповещений...")

    alert_types = ['cpu', 'memory', 'disk', 'temperature', 'humidity']
    severities = ['warning', 'critical']

    alerts_count = 0

    for i in range(20):  # Генерируем 20 тестовых оповещений
        alert_type = random.choice(alert_types)
        severity = random.choice(severities)

        # Реалистичные значения
        if alert_type == 'cpu':
            value = random.uniform(75, 95)
            threshold = 70 if severity == 'warning' else 90
            message = f"Высокая загрузка процессора: {value:.1f}%"
        elif alert_type == 'memory':
            value = random.uniform(80, 95)
            threshold = 80 if severity == 'warning' else 95
            message = f"Высокое использование памяти: {value:.1f}%"
        elif alert_type == 'disk':
            value = random.uniform(80, 95)
            threshold = 80 if severity == 'warning' else 95
            message = f"Мало места на диске: {value:.1f}%"
        elif alert_type == 'temperature':
            value = random.uniform(40, 55)
            threshold = 40 if severity == 'warning' else 50
            message = f"Высокая температура в ЦОД: {value:.1f}°C"
        else:  # humidity
            value = random.uniform(70, 90)
            threshold = 70 if severity == 'warning' else 85
            message = f"Высокая влажность в ЦОД: {value:.1f}%"

        # Случайное время в последние 3 дня
        timestamp = datetime.now() - timedelta(
            days=random.uniform(0, 3),
            hours=random.uniform(0, 24)
        )

        alert = AlertLog(
            timestamp=timestamp,
            alert_type=alert_type,
            severity=severity,
            message=message,
            value=value,
            threshold=threshold,
            resolved=random.choice([True, False, False])  # 2/3 разрешены
        )

        db.session.add(alert)
        alerts_count += 1

    try:
        db.session.commit()
        print(f"✅ Сгенерировано {alerts_count} демо-оповещений")
        return True
    except Exception as e:
        print(f"❌ Ошибка генерации оповещений: {e}")
        db.session.rollback()
        return False


def generate_demo_audit_logs():
    """Генерация демо-логов аудита"""
    print("Генерация демо-логов аудита...")

    users = User.query.all()
    if not users:
        print("⚠️ Нет пользователей для генерации аудит-логов")
        return False

    actions = [
        'login', 'logout', 'update_settings', 'create_user', 'delete_user',
        'export_config', 'backup_created', 'alert_resolved', 'system_check'
    ]

    resources = ['system', 'user_management', 'settings', 'alerts', 'backup']

    logs_count = 0

    for i in range(50):  # 50 записей аудита
        user = random.choice(users)
        action = random.choice(actions)
        resource = random.choice(resources)

        details_map = {
            'login': f'Успешный вход в систему',
            'logout': f'Выход из системы',
            'update_settings': f'Обновлены настройки {resource}',
            'create_user': f'Создан новый пользователь',
            'delete_user': f'Удален пользователь',
            'export_config': f'Экспорт конфигурации системы',
            'backup_created': f'Создана резервная копия',
            'alert_resolved': f'Разрешен инцидент',
            'system_check': f'Проверка состояния системы'
        }

        timestamp = datetime.now() - timedelta(
            days=random.uniform(0, 7),
            hours=random.uniform(0, 24)
        )

        audit_log = AuditLog(
            user_id=user.id,
            action=action,
            resource=resource,
            details=details_map.get(action, f'Действие {action}'),
            ip_address=f"192.168.1.{random.randint(10, 250)}",
            user_agent="Mozilla/5.0 (Demo Data Generator)",
            timestamp=timestamp
        )

        db.session.add(audit_log)
        logs_count += 1

    try:
        db.session.commit()
        print(f"✅ Сгенерировано {logs_count} записей аудита")
        return True
    except Exception as e:
        print(f"❌ Ошибка генерации аудит-логов: {e}")
        db.session.rollback()
        return False


def main():
    """Главная функция генерации демо-данных"""
    with app.app_context():
        print("🚀 Запуск генерации демо-данных для системы мониторинга ЦОД")
        print("=" * 60)

        # Генерируем метрики
        if generate_demo_metrics(days=7, points_per_day=288):
            print("✅ Метрики сгенерированы")
        else:
            print("❌ Ошибка генерации метрик")
            return

        # Генерируем оповещения
        if generate_demo_alerts():
            print("✅ Оповещения сгенерированы")
        else:
            print("❌ Ошибка генерации оповещений")

        # Генерируем аудит-логи
        if generate_demo_audit_logs():
            print("✅ Аудит-логи сгенерированы")
        else:
            print("❌ Ошибка генерации аудит-логов")

        print("=" * 60)
        print("🎉 Генерация демо-данных завершена!")
        print("\n📊 Статистика:")
        print(f"• Метрики: {SystemMetrics.query.count()} записей")
        print(f"• Оповещения: {AlertLog.query.count()} записей")
        print(f"• Аудит-логи: {AuditLog.query.count()} записей")
        print(f"• Пользователи: {User.query.count()}")

        print("\n🔄 Перезапустите приложение для обновления аналитики!")


if __name__ == "__main__":
    main()