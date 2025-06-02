# Система мониторинга ЦОД

Веб-приложение для мониторинга оборудования в центре обработки данных. Собирает метрики с серверов и сетевого оборудования, анализирует их и уведомляет о проблемах.

## Возможности

- Сбор данных с оборудования через SNMP, IPMI, API
- Мониторинг серверов, сети, систем охлаждения и питания
- Дашборды с графиками и метриками в реальном времени
- Система оповещений при превышении пороговых значений
- Администрирование пользователей и настроек
- Экспорт отчетов и резервное копирование

## Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/lleviathan1/datacenter-monitor
cd datacenter-monitor

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить приложение
python app.py
```

Откройте http://localhost:5000 в браузере.

**Логин по умолчанию:** admin / admin123

## Технологии

- **Backend:** Python, Flask, SQLAlchemy
- **Frontend:** Bootstrap 5, Chart.js, jQuery
- **База данных:** SQLite
- **Мониторинг:** pysnmp, psutil, requests

## Структура

```
├── app.py                  # Основное приложение Flask
├── config.py               # Конфигурация приложения
├── analytics/              # Модуль аналитики
│   ├── analytics_service.py    # Сервис аналитики
│   └── anomaly_detector.py     # Детектор аномалий
├── collectors/             # Сборщики данных
│   ├── network_metrics.py      # Сбор сетевых метрик
│   └── system_metrics.py       # Сбор системных метрик
├── models/                 # Модели базы данных
│   ├── monitoring.py           # Модели мониторинга
│   ├── settings.py             # Модели настроек
│   └── users.py                # Модели пользователей
├── services/               # Бизнес-сервисы
│   ├── admin_service.py        # Администрирование
│   └── notification_service.py # Уведомления
├── static/                 # Статические файлы
│   ├── css/                    # Стили 
│   └── js/                     # JavaScript
├── templates/              # HTML шаблоны
├── database/               # База данных
└── requirements.txt        # Python зависимости
```

## Настройка

Основные настройки в файле `app.py`. Для production создайте `.env` файл:

```
FLASK_ENV=production
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///production.db
```

## Дипломная работа

Проект выполнен в рамках дипломной работы

**Тема:** "Разработка программного обеспечения макета сбора и анализа статистики работы оборудования в интересах должностного лица ЦОД"