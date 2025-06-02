class Dashboard {
    constructor() {
        this.charts = {};
        this.updateInterval = 5000; // 5 секунд
        this.isActive = true;
        this.init();
    }

    init() {
        this.initCharts();
        this.updateMetrics();
        this.updateStatus();
        this.updateCharts();
        this.updateAlerts();

        // Главный цикл обновления
        this.updateLoop = setInterval(() => {
            if (this.isActive) {
                this.updateMetrics();
                this.updateStatus();
                this.updateCharts();
                this.updateAlerts();
            }
        }, this.updateInterval);

        // Обработчики кнопок
        this.setupEventHandlers();
    }

    setupEventHandlers() {
        // Кнопка паузы/продолжения
        const pauseBtn = document.getElementById('pauseBtn');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.togglePause());
        }

        // Кнопка обновления
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }
    }

    async updateMetrics() {
        try {
            const response = await fetch('/api/metrics');
            const data = await response.json();

            // Обновляем метрики на странице
            this.updateMetricCard('cpu', data.cpu_percent, '%');
            this.updateMetricCard('memory', data.memory_percent, '%', `${data.memory_used_gb}/${data.memory_total_gb} ГБ`);
            this.updateMetricCard('disk', data.disk_percent, '%', `${data.disk_used_gb}/${data.disk_total_gb} ГБ`);
            this.updateMetricCard('network', data.network_speed_down || 0, 'KB/s', `↓${data.network_speed_down || 0} ↑${data.network_speed_up || 0}`);
            this.updateMetricCard('temperature', data.temperature, '°C');
            this.updateMetricCard('humidity', data.humidity, '%');
            this.updateMetricCard('pressure', data.pressure, 'ГПа');

            // Обновляем прогресс-бары с правильной логикой
            this.updateProgressBar('cpu', data.cpu_percent);
            this.updateProgressBar('memory', data.memory_percent);
            this.updateProgressBar('disk', data.disk_percent);
            this.updateProgressBar('network', data.network_speed_down || 0);
            this.updateProgressBar('temperature', data.temperature);
            this.updateProgressBar('humidity', data.humidity);

            // Обновляем время последнего обновления
            const lastUpdateElement = document.getElementById('lastUpdate');
            if (lastUpdateElement) {
                lastUpdateElement.textContent = data.timestamp || new Date().toLocaleTimeString();
            }

        } catch (error) {
            console.error('Ошибка обновления метрик:', error);
        }
    }

    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();

            // Обновляем индикаторы статуса в верхней панели
            this.updateStatusIndicator('cpu', status.cpu_status);
            this.updateStatusIndicator('memory', status.memory_status);
            this.updateStatusIndicator('disk', status.disk_status);
            this.updateStatusIndicator('temperature', status.temperature_status);
            this.updateStatusIndicator('humidity', status.humidity_status);

        } catch (error) {
            console.error('Ошибка обновления статуса:', error);
        }
    }

    updateStatusIndicator(metricType, statusColor) {
        // Находим индикатор по типу метрики
        const indicator = document.querySelector(`[data-metric="${metricType}"]`);
        if (!indicator) return;

        // Удаляем старые классы цветов
        indicator.classList.remove('bg-success', 'bg-warning', 'bg-danger');

        // Добавляем новый класс цвета
        switch(statusColor) {
            case 'success':
                indicator.classList.add('bg-success');
                break;
            case 'warning':
                indicator.classList.add('bg-warning');
                break;
            case 'danger':
                indicator.classList.add('bg-danger');
                break;
            default:
                indicator.classList.add('bg-success'); // По умолчанию зеленый
        }
    }

    updateMetricCard(metric, value, unit, detail = '') {
        const valueElement = document.getElementById(`${metric}-value`);
        const detailElement = document.getElementById(`${metric}-detail`);

        if (valueElement) {
            if (typeof value === 'number') {
                valueElement.textContent = `${value.toFixed(1)}${unit}`;
            } else {
                valueElement.textContent = `${value}${unit}`;
            }
        }

        if (detailElement && detail) {
            detailElement.textContent = detail;
        }
    }

    updateProgressBar(metric, value) {
        const progressBar = document.getElementById(`${metric}-progress`);
        if (progressBar) {
            let percentage;

            // Специальная логика для разных типов метрик
            if (metric === 'network') {
                // Нормализуем скорость сети (предполагаем максимум 1000 KB/s для отображения)
                percentage = Math.min(100, Math.max(0, (value / 1000) * 100));
            } else if (metric === 'temperature') {
                // Для температуры (предполагаем диапазон 15-50°C для прогресс-бара)
                const tempMin = 15;
                const tempMax = 50;
                percentage = Math.min(100, Math.max(0, ((value - tempMin) / (tempMax - tempMin)) * 100));
            } else if (metric === 'pressure') {
                // Для давления (предполагаем диапазон 1000-1030 ГПа)
                const pressMin = 1000;
                const pressMax = 1030;
                percentage = Math.min(100, Math.max(0, ((value - pressMin) / (pressMax - pressMin)) * 100));
            } else {
                // Для процентных значений (CPU, память, диск, влажность)
                percentage = Math.min(100, Math.max(0, value));
            }

            progressBar.style.width = `${percentage}%`;

            // Обновляем цвет прогресс-бара в зависимости от значения
            progressBar.classList.remove('bg-success', 'bg-warning', 'bg-danger');

            // Определяем цвет в зависимости от типа метрики и значения
            if (metric === 'temperature') {
                if (value >= 40) {
                    progressBar.classList.add('bg-danger');
                } else if (value >= 30) {
                    progressBar.classList.add('bg-warning');
                } else {
                    progressBar.classList.add('bg-success');
                }
            } else if (metric === 'humidity') {
                if (value >= 70) {
                    progressBar.classList.add('bg-warning');
                } else if (value >= 80) {
                    progressBar.classList.add('bg-danger');
                } else {
                    progressBar.classList.add('bg-success');
                }
            } else if (metric === 'network') {
                // Для сети цвет зависит от загрузки
                if (value >= 800) {
                    progressBar.classList.add('bg-danger');
                } else if (value >= 500) {
                    progressBar.classList.add('bg-warning');
                } else {
                    progressBar.classList.add('bg-success');
                }
            } else if (metric === 'pressure') {
                // Для давления норма около 1013-1015 ГПа
                if (value < 1005 || value > 1025) {
                    progressBar.classList.add('bg-warning');
                } else {
                    progressBar.classList.add('bg-success');
                }
            } else {
                // Для остальных метрик (CPU, память, диск)
                if (percentage >= 90) {
                    progressBar.classList.add('bg-danger');
                } else if (percentage >= 70) {
                    progressBar.classList.add('bg-warning');
                } else {
                    progressBar.classList.add('bg-success');
                }
            }
        }
    }

    async updateCharts() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();

            this.updateSystemPerformanceChart(data);
            this.updateNetworkChart(data);
            this.updateEnvironmentChart(data);

        } catch (error) {
            console.error('Ошибка обновления графиков:', error);
        }
    }

    async updateAlerts() {
        try {
            const response = await fetch('/api/alerts');
            const alerts = await response.json();

            const alertsContainer = document.getElementById('alertsContainer');
            if (!alertsContainer) return;

            if (alerts.length === 0) {
                alertsContainer.innerHTML = '<p class="text-muted">Нет недавних оповещений</p>';
                return;
            }

            alertsContainer.innerHTML = alerts.slice(0, 5).map(alert => `
                <div class="alert alert-${alert.severity === 'critical' ? 'danger' : 'warning'} alert-sm mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${alert.alert_type.toUpperCase()}</strong><br>
                            <small>${alert.message}</small>
                        </div>
                        <small class="text-muted">${new Date(alert.timestamp).toLocaleString()}</small>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Ошибка обновления оповещений:', error);
        }
    }

    initCharts() {
        this.initSystemPerformanceChart();
        this.initNetworkChart();
        this.initEnvironmentChart();
    }

    initSystemPerformanceChart() {
        const ctx = document.getElementById('systemPerformanceChart');
        if (!ctx) return;

        this.charts.systemPerformance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU (%)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.4
                    },
                    {
                        label: 'RAM (%)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.4
                    },
                    {
                        label: 'Диск (%)',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    }

    initNetworkChart() {
        const ctx = document.getElementById('networkChart');
        if (!ctx) return;

        this.charts.network = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Входящий (KB/s)',
                        data: [],
                        borderColor: 'rgb(255, 205, 86)',
                        backgroundColor: 'rgba(255, 205, 86, 0.1)',
                        tension: 0.4
                    },
                    {
                        label: 'Исходящий (KB/s)',
                        data: [],
                        borderColor: 'rgb(153, 102, 255)',
                        backgroundColor: 'rgba(153, 102, 255, 0.1)',
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    }

    initEnvironmentChart() {
        const ctx = document.getElementById('environmentChart');
        if (!ctx) return;

        this.charts.environment = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Температура (°C)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Влажность (%)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Температура (°C)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Влажность (%)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    }

    updateSystemPerformanceChart(data) {
        if (!this.charts.systemPerformance || !data.timestamps) return;

        this.charts.systemPerformance.data.labels = data.timestamps;
        this.charts.systemPerformance.data.datasets[0].data = data.cpu_percent || [];
        this.charts.systemPerformance.data.datasets[1].data = data.memory_percent || [];
        this.charts.systemPerformance.data.datasets[2].data = data.disk_percent || [];
        this.charts.systemPerformance.update('none');
    }

    updateNetworkChart(data) {
        if (!this.charts.network || !data.timestamps) return;

        this.charts.network.data.labels = data.timestamps;
        this.charts.network.data.datasets[0].data = data.network_recv || [];
        this.charts.network.data.datasets[1].data = data.network_sent || [];
        this.charts.network.update('none');
    }

    updateEnvironmentChart(data) {
        if (!this.charts.environment || !data.timestamps) return;

        this.charts.environment.data.labels = data.timestamps;
        this.charts.environment.data.datasets[0].data = data.temperature || [];
        this.charts.environment.data.datasets[1].data = data.humidity || [];
        this.charts.environment.update('none');
    }

    togglePause() {
        this.isActive = !this.isActive;
        const pauseBtn = document.getElementById('pauseBtn');
        const icon = pauseBtn.querySelector('i');
        const text = pauseBtn.querySelector('span');

        if (this.isActive) {
            icon.className = 'fas fa-pause me-1';
            text.textContent = 'Пауза';
            pauseBtn.className = 'btn btn-outline-light btn-sm';
        } else {
            icon.className = 'fas fa-play me-1';
            text.textContent = 'Продолжить';
            pauseBtn.className = 'btn btn-warning btn-sm';
        }
    }

    refreshData() {
        if (this.isActive) {
            this.updateMetrics();
            this.updateStatus();
            this.updateCharts();
            this.updateAlerts();
        }
    }

    // Тестовые функции для проверки индикаторов
    testStatusIndicators() {
        console.log('🧪 Тестирование индикаторов статуса...');

        // Сначала все зеленые
        setTimeout(() => {
            console.log('Все зеленые');
            this.updateStatusIndicator('cpu', 'success');
            this.updateStatusIndicator('memory', 'success');
            this.updateStatusIndicator('disk', 'success');
            this.updateStatusIndicator('temperature', 'success');
            this.updateStatusIndicator('humidity', 'success');
        }, 1000);

        // Затем желтые предупреждения
        setTimeout(() => {
            console.log('Предупреждения (желтые)');
            this.updateStatusIndicator('cpu', 'warning');
            this.updateStatusIndicator('memory', 'warning');
        }, 3000);

        // Затем красные критические
        setTimeout(() => {
            console.log('Критические (красные)');
            this.updateStatusIndicator('temperature', 'danger');
            this.updateStatusIndicator('humidity', 'danger');
        }, 5000);

        // Возвращаем к реальным статусам
        setTimeout(() => {
            console.log('Возврат к реальным статусам');
            this.updateStatus();
        }, 7000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new Dashboard();
});