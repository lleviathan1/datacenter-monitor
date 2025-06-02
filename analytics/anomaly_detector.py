import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


class AnomalyDetector:
    """Класс для обнаружения аномалий в метриках ЦОД"""

    def __init__(self, contamination=0.1, window_size=50):
        self.contamination = contamination  # Ожидаемая доля аномалий
        self.window_size = window_size  # Размер окна для анализа
        self.models = {}  # Модели для каждой метрики
        self.scalers = {}  # Нормализаторы
        self.baselines = {}  # Базовые значения метрик
        self.is_trained = False

    def prepare_data(self, metrics_data: List[Dict]) -> pd.DataFrame:
        """Подготовка данных для анализа"""
        if not metrics_data:
            return pd.DataFrame()

        df = pd.DataFrame(metrics_data)

        # Выбираем только числовые колонки для анализа
        numeric_columns = [
            'cpu_percent', 'memory_percent', 'disk_percent',
            'temperature', 'humidity', 'pressure',
            'network_sent_mb', 'network_recv_mb',
            'processes_count'
        ]

        # Оставляем только существующие колонки
        available_columns = [col for col in numeric_columns if col in df.columns]

        if not available_columns:
            return pd.DataFrame()

        # Заполняем пропущенные значения
        df[available_columns] = df[available_columns].fillna(method='ffill')
        df[available_columns] = df[available_columns].fillna(0)

        return df[available_columns]

    def train_models(self, historical_data: List[Dict]):
        """Обучение моделей обнаружения аномалий"""
        try:
            df = self.prepare_data(historical_data)

            if df.empty or len(df) < 10:
                print("Недостаточно данных для обучения моделей")
                return False

            for column in df.columns:
                if df[column].std() == 0:  # Пропускаем константные значения
                    continue

                # Нормализация данных
                scaler = StandardScaler()
                data_scaled = scaler.fit_transform(df[[column]])

                # Обучение модели Isolation Forest
                model = IsolationForest(
                    contamination=self.contamination,
                    random_state=42,
                    n_estimators=100
                )
                model.fit(data_scaled)

                # Сохраняем модель и скейлер
                self.models[column] = model
                self.scalers[column] = scaler

                # Вычисляем базовые статистики
                self.baselines[column] = {
                    'mean': df[column].mean(),
                    'std': df[column].std(),
                    'min': df[column].min(),
                    'max': df[column].max(),
                    'q25': df[column].quantile(0.25),
                    'q75': df[column].quantile(0.75)
                }

            self.is_trained = True
            print(f"Обучены модели для {len(self.models)} метрик")
            return True

        except Exception as e:
            print(f"Ошибка обучения моделей: {e}")
            return False

    def detect_anomalies(self, current_metrics: Dict) -> Dict:
        """Обнаружение аномалий в текущих метриках"""
        if not self.is_trained:
            return {'anomalies': [], 'scores': {}}

        anomalies = []
        scores = {}

        try:
            for metric_name, value in current_metrics.items():
                if metric_name not in self.models or not isinstance(value, (int, float)):
                    continue

                model = self.models[metric_name]
                scaler = self.scalers[metric_name]
                baseline = self.baselines[metric_name]

                # Нормализация текущего значения
                value_scaled = scaler.transform([[value]])

                # Получение аномальности (score)
                anomaly_score = model.decision_function(value_scaled)[0]
                is_anomaly = model.predict(value_scaled)[0] == -1

                scores[metric_name] = {
                    'score': float(anomaly_score),
                    'is_anomaly': bool(is_anomaly),
                    'deviation_from_mean': abs(value - baseline['mean']) / baseline['std'] if baseline['std'] > 0 else 0
                }

                # Если обнаружена аномалия
                if is_anomaly:
                    severity = self._calculate_severity(value, baseline, anomaly_score)

                    anomalies.append({
                        'metric': metric_name,
                        'value': value,
                        'score': anomaly_score,
                        'severity': severity,
                        'baseline_mean': baseline['mean'],
                        'description': self._generate_anomaly_description(metric_name, value, baseline)
                    })

            return {
                'anomalies': anomalies,
                'scores': scores,
                'total_anomalies': len(anomalies)
            }

        except Exception as e:
            print(f"Ошибка обнаружения аномалий: {e}")
            return {'anomalies': [], 'scores': {}}

    def _calculate_severity(self, value: float, baseline: Dict, anomaly_score: float) -> str:
        """Вычисление серьезности аномалии"""
        deviation = abs(value - baseline['mean']) / baseline['std'] if baseline['std'] > 0 else 0

        if anomaly_score < -0.5 or deviation > 3:
            return 'critical'
        elif anomaly_score < -0.3 or deviation > 2:
            return 'warning'
        else:
            return 'info'

    def _generate_anomaly_description(self, metric: str, value: float, baseline: Dict) -> str:
        """Генерация описания аномалии"""
        mean_val = baseline['mean']

        descriptions = {
            'cpu_percent': f"Загрузка ЦП {value:.1f}% значительно отличается от нормы ({mean_val:.1f}%)",
            'memory_percent': f"Использование памяти {value:.1f}% аномально для системы (норма {mean_val:.1f}%)",
            'disk_percent': f"Использование диска {value:.1f}% отклоняется от типичных значений ({mean_val:.1f}%)",
            'temperature': f"Температура {value:.1f}°C не соответствует обычному диапазону (норма {mean_val:.1f}°C)",
            'humidity': f"Влажность {value:.1f}% выходит за пределы нормального диапазона ({mean_val:.1f}%)",
            'network_sent_mb': f"Исходящий трафик {value:.1f}MB аномален (обычно {mean_val:.1f}MB)",
            'network_recv_mb': f"Входящий трафик {value:.1f}MB необычен (обычно {mean_val:.1f}MB)"
        }

        return descriptions.get(metric, f"Аномальное значение {metric}: {value:.1f}")


class TrendPredictor:
    """Класс для прогнозирования трендов метрик"""

    def __init__(self, forecast_hours=6):
        self.forecast_hours = forecast_hours
        self.trend_models = {}

    def analyze_trends(self, historical_data: List[Dict]) -> Dict:
        """Анализ трендов в исторических данных"""
        try:
            df = pd.DataFrame(historical_data)

            if df.empty or len(df) < 10:
                return {'trends': {}, 'forecasts': {}}

            # Преобразуем timestamp в datetime
            if 'timestamp' in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('datetime')

            trends = {}
            forecasts = {}

            numeric_columns = ['cpu_percent', 'memory_percent', 'disk_percent', 'temperature', 'humidity']

            for column in numeric_columns:
                if column in df.columns:
                    trend_analysis = self._analyze_single_trend(df[column].values)
                    trends[column] = trend_analysis

                    # Простое прогнозирование на основе тренда
                    forecast = self._simple_forecast(df[column].values, hours=self.forecast_hours)
                    forecasts[column] = forecast

            return {
                'trends': trends,
                'forecasts': forecasts,
                'analysis_time': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Ошибка анализа трендов: {e}")
            return {'trends': {}, 'forecasts': {}}

    def _analyze_single_trend(self, data: np.ndarray) -> Dict:
        """Анализ тренда для одной метрики"""
        if len(data) < 3:
            return {'direction': 'stable', 'strength': 0, 'change_rate': 0}

        # Вычисляем коэффициент корреляции с временем (тренд)
        x = np.arange(len(data))
        correlation = np.corrcoef(x, data)[0, 1] if not np.isnan(data).any() else 0

        # Определяем направление тренда
        if correlation > 0.3:
            direction = 'increasing'
        elif correlation < -0.3:
            direction = 'decreasing'
        else:
            direction = 'stable'

        # Вычисляем скорость изменения
        if len(data) >= 2:
            change_rate = (data[-1] - data[0]) / len(data)
        else:
            change_rate = 0

        return {
            'direction': direction,
            'strength': abs(correlation),
            'change_rate': float(change_rate),
            'current_value': float(data[-1]) if len(data) > 0 else 0,
            'volatility': float(np.std(data)) if len(data) > 1 else 0
        }

    def _simple_forecast(self, data: np.ndarray, hours: int) -> Dict:
        """Простое прогнозирование на основе линейного тренда"""
        if len(data) < 3:
            return {'predicted_values': [], 'confidence': 'low'}

        # Используем простую линейную экстраполяцию
        x = np.arange(len(data))

        # Линейная регрессия
        coeffs = np.polyfit(x, data, 1)

        # Прогнозируем следующие точки
        future_x = np.arange(len(data), len(data) + hours)
        predicted = np.polyval(coeffs, future_x)

        # Оценка уверенности на основе R²
        fitted = np.polyval(coeffs, x)
        ss_res = np.sum((data - fitted) ** 2)
        ss_tot = np.sum((data - np.mean(data)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        confidence = 'high' if r_squared > 0.7 else 'medium' if r_squared > 0.4 else 'low'

        return {
            'predicted_values': predicted.tolist(),
            'confidence': confidence,
            'r_squared': float(r_squared),
            'trend_slope': float(coeffs[0])
        }


class CorrelationAnalyzer:
    """Класс для корреляционного анализа метрик"""

    def analyze_correlations(self, historical_data: List[Dict]) -> Dict:
        """Анализ корреляций между метриками"""
        try:
            df = pd.DataFrame(historical_data)

            if df.empty:
                return {'correlations': {}, 'insights': []}

            numeric_columns = [
                'cpu_percent', 'memory_percent', 'disk_percent',
                'temperature', 'humidity', 'network_sent_mb', 'network_recv_mb'
            ]

            # Оставляем только доступные колонки
            available_columns = [col for col in numeric_columns if col in df.columns]

            if len(available_columns) < 2:
                return {'correlations': {}, 'insights': []}

            # Вычисляем корреляционную матрицу
            corr_matrix = df[available_columns].corr()

            # Находим значимые корреляции
            significant_correlations = []
            insights = []

            for i, col1 in enumerate(available_columns):
                for j, col2 in enumerate(available_columns):
                    if i < j:  # Избегаем дублирования
                        correlation = corr_matrix.loc[col1, col2]

                        if not np.isnan(correlation) and abs(correlation) > 0.5:
                            significant_correlations.append({
                                'metric1': col1,
                                'metric2': col2,
                                'correlation': float(correlation),
                                'strength': self._correlation_strength(correlation)
                            })

                            # Генерируем инсайт
                            insight = self._generate_correlation_insight(col1, col2, correlation)
                            if insight:
                                insights.append(insight)

            return {
                'correlations': significant_correlations,
                'correlation_matrix': corr_matrix.to_dict(),
                'insights': insights,
                'analysis_time': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Ошибка корреляционного анализа: {e}")
            return {'correlations': {}, 'insights': []}

    def _correlation_strength(self, correlation: float) -> str:
        """Определение силы корреляции"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.8:
            return 'very_strong'
        elif abs_corr >= 0.6:
            return 'strong'
        elif abs_corr >= 0.4:
            return 'moderate'
        else:
            return 'weak'

    def _generate_correlation_insight(self, metric1: str, metric2: str, correlation: float) -> Optional[str]:
        """Генерация инсайтов на основе корреляций"""
        insights_map = {
            ('cpu_percent',
             'temperature'): f"Высокая загрузка ЦП коррелирует с температурой (r={correlation:.2f}). Следите за охлаждением при высокой нагрузке.",
            ('memory_percent',
             'cpu_percent'): f"Использование памяти связано с загрузкой ЦП (r={correlation:.2f}). Возможна нехватка ресурсов.",
            ('temperature',
             'humidity'): f"Температура и влажность взаимосвязаны (r={correlation:.2f}). Контролируйте климат в ЦОД.",
            ('network_sent_mb',
             'network_recv_mb'): f"Входящий и исходящий трафик коррелируют (r={correlation:.2f}). Симметричная нагрузка на сеть."
        }

        # Проверяем прямое соответствие и обратное
        key1 = (metric1, metric2)
        key2 = (metric2, metric1)

        return insights_map.get(key1) or insights_map.get(key2)