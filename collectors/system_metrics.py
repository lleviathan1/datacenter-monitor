import psutil
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List
from models.monitoring import db, SystemMetrics, AlertLog
from models.settings import AlertSettings


class EnhancedSystemMetricsCollector:
    """Расширенный класс для сбора системных метрик и датчиков ЦОД"""

    def __init__(self):
        self.data_history = {
            'timestamps': [],
            'cpu_percent': [],
            'memory_percent': [],
            'disk_percent': [],
            'network_sent': [],
            'network_recv': [],
            'temperature': [],
            'humidity': [],
            'pressure': []
        }
        self.max_points = 50
        self.last_network_stats = None
        self.baseline_pressure = random.uniform(1010, 1020)  # Базовое давление

    def get_current_metrics(self) -> Dict:
        """Получить расширенные текущие метрики системы"""
        # Базовые системные метрики
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Расширенные сетевые метрики
        network = psutil.net_io_counters()
        network_detailed = self._get_network_detailed()

        # Симуляция датчиков ЦОД
        datacenter_sensors = self._simulate_datacenter_sensors()

        # Дополнительные системные данные
        processes_count = len(psutil.pids())
        uptime_seconds = time.time() - psutil.boot_time()

        metrics = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'datetime': datetime.now(),

            # Системные метрики
            'cpu_percent': round(cpu_percent, 1),
            'memory_percent': round(memory.percent, 1),
            'memory_used_gb': round(memory.used / (1024 ** 3), 1),
            'memory_total_gb': round(memory.total / (1024 ** 3), 1),
            'disk_percent': round((disk.used / disk.total) * 100, 1),
            'disk_used_gb': round(disk.used / (1024 ** 3), 1),
            'disk_total_gb': round(disk.total / (1024 ** 3), 1),

            # Сетевые метрики
            'network_sent_mb': round(network.bytes_sent / (1024 ** 2), 1),
            'network_recv_mb': round(network.bytes_recv / (1024 ** 2), 1),
            'network_packets_sent': network.packets_sent,
            'network_packets_recv': network.packets_recv,
            'network_errors_in': network.errin,
            'network_errors_out': network.errout,
            'network_speed_up': network_detailed['speed_up'],
            'network_speed_down': network_detailed['speed_down'],

            # Датчики ЦОД
            'temperature': datacenter_sensors['temperature'],
            'humidity': datacenter_sensors['humidity'],
            'pressure': datacenter_sensors['pressure'],

            # Дополнительные метрики
            'uptime_seconds': int(uptime_seconds),
            'uptime': self._format_uptime(uptime_seconds),
            'processes_count': processes_count
        }

        return metrics

    def _get_network_detailed(self) -> Dict:
        """Получить детальную сетевую статистику"""
        current_stats = psutil.net_io_counters()

        if self.last_network_stats is None:
            self.last_network_stats = {
                'bytes_sent': current_stats.bytes_sent,
                'bytes_recv': current_stats.bytes_recv,
                'timestamp': time.time()
            }
            return {'speed_up': 0, 'speed_down': 0}

        time_diff = time.time() - self.last_network_stats['timestamp']
        if time_diff > 0:
            speed_up = (current_stats.bytes_sent - self.last_network_stats['bytes_sent']) / time_diff / 1024  # KB/s
            speed_down = (current_stats.bytes_recv - self.last_network_stats['bytes_recv']) / time_diff / 1024  # KB/s
        else:
            speed_up = speed_down = 0

        self.last_network_stats = {
            'bytes_sent': current_stats.bytes_sent,
            'bytes_recv': current_stats.bytes_recv,
            'timestamp': time.time()
        }

        return {
            'speed_up': round(max(0, speed_up), 1),
            'speed_down': round(max(0, speed_down), 1)
        }

    def _simulate_datacenter_sensors(self) -> Dict:
        """Симуляция датчиков ЦОД для демонстрации"""
        # Температура зависит от загрузки CPU
        base_temp = 25 + (psutil.cpu_percent() * 0.3)  # 25°C + нагрузка
        temperature = base_temp + random.uniform(-2, 3)

        # Влажность с небольшими колебаниями
        base_humidity = 45
        humidity = base_humidity + random.uniform(-10, 15)

        # Атмосферное давление с небольшими изменениями
        pressure_variation = random.uniform(-2, 2)
        pressure = self.baseline_pressure + pressure_variation

        return {
            'temperature': round(max(20, min(60, temperature)), 1),
            'humidity': round(max(30, min(80, humidity)), 1),
            'pressure': round(pressure, 1)
        }

    def _format_uptime(self, uptime_seconds: float) -> str:
        """Форматирование времени работы"""
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)

        if days > 0:
            return f"{days}д {hours}ч {minutes}м"
        else:
            return f"{hours}ч {minutes}м"

    def save_to_database(self, metrics: Dict):
        """Сохранение метрик в базу данных"""
        try:
            metric_record = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=metrics['cpu_percent'],
                memory_percent=metrics['memory_percent'],
                memory_used_gb=metrics['memory_used_gb'],
                memory_total_gb=metrics['memory_total_gb'],
                disk_percent=metrics['disk_percent'],
                disk_used_gb=metrics['disk_used_gb'],
                disk_total_gb=metrics['disk_total_gb'],
                network_sent_mb=metrics['network_sent_mb'],
                network_recv_mb=metrics['network_recv_mb'],
                network_packets_sent=metrics['network_packets_sent'],
                network_packets_recv=metrics['network_packets_recv'],
                network_errors_in=metrics['network_errors_in'],
                network_errors_out=metrics['network_errors_out'],
                temperature=metrics['temperature'],
                humidity=metrics['humidity'],
                pressure=metrics['pressure'],
                uptime_seconds=metrics['uptime_seconds'],
                processes_count=metrics['processes_count']
            )

            db.session.add(metric_record)
            db.session.commit()

        except Exception as e:
            print(f"Ошибка сохранения в БД: {e}")
            db.session.rollback()

    def get_historical_data(self, hours: int = 24) -> List[Dict]:
        """Получение исторических данных из БД"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            records = SystemMetrics.query.filter(
                SystemMetrics.timestamp >= since
            ).order_by(SystemMetrics.timestamp.desc()).limit(200).all()

            return [record.to_dict() for record in reversed(records)]
        except Exception as e:
            print(f"Ошибка получения данных из БД: {e}")
            return []

    def add_to_history(self, metrics: Dict):
        """Добавить метрики в историю для графиков"""
        self.data_history['timestamps'].append(metrics['timestamp'])
        self.data_history['cpu_percent'].append(metrics['cpu_percent'])
        self.data_history['memory_percent'].append(metrics['memory_percent'])
        self.data_history['disk_percent'].append(metrics['disk_percent'])
        self.data_history['network_sent'].append(metrics.get('network_speed_up', 0))
        self.data_history['network_recv'].append(metrics.get('network_speed_down', 0))
        self.data_history['temperature'].append(metrics['temperature'])
        self.data_history['humidity'].append(metrics['humidity'])
        self.data_history['pressure'].append(metrics['pressure'])

        # Ограничиваем количество точек
        for key in self.data_history:
            if len(self.data_history[key]) > self.max_points:
                self.data_history[key] = self.data_history[key][-self.max_points:]

    def get_history(self) -> Dict:
        """Получить историю метрик для графиков"""
        return self.data_history

    def check_alerts(self, metrics: Dict, alert_manager):
        """Проверка пороговых значений и создание оповещений"""
        try:
            alert_settings = {s.metric_type: s for s in AlertSettings.query.all()}

            # Проверяем каждую метрику
            checks = [
                ('cpu', metrics['cpu_percent']),
                ('memory', metrics['memory_percent']),
                ('disk', metrics['disk_percent']),
                ('temperature', metrics['temperature']),
                ('humidity', metrics['humidity'])
            ]

            for metric_type, value in checks:
                setting = alert_settings.get(metric_type)
                if not setting:
                    continue

                # Определяем уровень предупреждения
                severity = None
                threshold = None

                if value >= setting.critical_threshold:
                    severity = 'critical'
                    threshold = setting.critical_threshold
                elif value >= setting.warning_threshold:
                    severity = 'warning'
                    threshold = setting.warning_threshold

                if severity:
                    # Проверяем, не было ли недавно такого же оповещения
                    recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
                    recent_alert = AlertLog.query.filter(
                        AlertLog.alert_type == metric_type,
                        AlertLog.severity == severity,
                        AlertLog.timestamp >= recent_cutoff,
                        AlertLog.resolved == False
                    ).first()

                    if not recent_alert:
                        # Создаем новое оповещение
                        message = self._generate_alert_message(metric_type, value, severity)
                        alert_manager.process_alert(
                            alert_type=metric_type,
                            severity=severity,
                            value=value,
                            threshold=threshold,
                            message=message
                        )

        except Exception as e:
            print(f"Ошибка проверки оповещений: {e}")

    def _generate_alert_message(self, metric_type: str, value: float, severity: str) -> str:
        """Генерация сообщения для оповещения"""
        metric_names = {
            'cpu': 'Загрузка процессора',
            'memory': 'Использование памяти',
            'disk': 'Заполненность диска',
            'temperature': 'Температура в ЦОД',
            'humidity': 'Влажность в ЦОД'
        }

        units = {
            'cpu': '%',
            'memory': '%',
            'disk': '%',
            'temperature': '°C',
            'humidity': '%'
        }

        metric_name = metric_names.get(metric_type, metric_type)
        unit = units.get(metric_type, '')

        severity_text = {
            'warning': 'превышает предупредительный уровень',
            'critical': 'достигла критического уровня'
        }

        return f"{metric_name} {severity_text.get(severity, 'превышена')}: {value}{unit}"

    def get_status_color(self, metric_type: str, value: float) -> str:
        """Получить цвет статуса для метрики"""
        try:
            setting = AlertSettings.query.filter_by(metric_type=metric_type).first()
            if not setting:
                return 'success'  # По умолчанию зеленый

            if value >= setting.critical_threshold:
                return 'danger'  # Красный
            elif value >= setting.warning_threshold:
                return 'warning'  # Желтый
            else:
                return 'success'  # Зеленый

        except Exception as e:
            print(f"Ошибка определения статуса: {e}")
            return 'secondary'  # Серый при ошибке