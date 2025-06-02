class AdminPanel {
    constructor() {
        this.updateInterval = 30000; // 30 секунд для админки
        this.defaultSettings = this.loadDefaultSettings();
        this.originalSettings = {}; // Исходные настройки при загрузке
        this.hasUnsavedChanges = false; // Флаг несохраненных изменений
        this.currentMode = 'current'; // 'current' или 'default'
        this.customDefaults = {}; // Пользовательские настройки по умолчанию
        this.init();
    }

    init() {
        console.log('🚀 Инициализация админки...');

        // Ждем загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.startInit());
        } else {
            this.startInit();
        }
    }

    startInit() {
        console.log('📊 Запуск загрузки данных...');

        // Загружаем данные последовательно
        this.loadStats();
        this.loadAlertSettings();
        this.loadNotificationSettings();
        this.loadActiveAlerts();
        this.loadUsers();
        this.loadAuditLogs();

        // Настройка обработчиков форм
        this.setupEventHandlers();

        // Автообновление статистики
        setInterval(() => {
            this.loadStats();
            this.loadActiveAlerts();
        }, this.updateInterval);
    }

    setupEventHandlers() {
        // Обработчик формы настроек оповещений
        const alertForm = document.getElementById('alert-settings-form');
        if (alertForm) {
            alertForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveAlertSettings();
            });
        }

        // Обработчик формы email настроек
        const emailForm = document.getElementById('email-settings-form');
        if (emailForm) {
            emailForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveNotificationSettings();
            });
        }

        console.log('✅ Обработчики событий настроены');
    }

    loadDefaultSettings() {
        // Загружаем пользовательские умолчания из localStorage или используем системные
        const savedDefaults = localStorage.getItem('admin_default_settings');
        if (savedDefaults) {
            try {
                return JSON.parse(savedDefaults);
            } catch (e) {
                console.error('Ошибка парсинга умолчаний:', e);
            }
        }

        // Системные умолчания - оптимальные значения для ЦОД
        return {
            'cpu': { warning: 70, critical: 85, email: true, escalation: 15 },
            'memory': { warning: 75, critical: 90, email: true, escalation: 10 },
            'disk': { warning: 80, critical: 90, email: true, escalation: 30 },
            'temperature': { warning: 30, critical: 40, email: true, escalation: 5 },
            'humidity': { warning: 65, critical: 80, email: false, escalation: 60 }
        };
    }

    async loadStats() {
        try {
            console.log('📈 Загрузка статистики...');
            const response = await fetch('/api/alerts/stats');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const stats = await response.json();
            console.log('Статистика получена:', stats);

            // Обновляем элементы статистики
            this.updateElement('total-alerts-24h', stats.total_alerts_24h || 0);
            this.updateElement('critical-alerts-24h', stats.critical_alerts_24h || 0);
            this.updateElement('resolved-alerts-24h', stats.resolved_alerts_24h || 0);
            this.updateElement('active-alerts', stats.active_alerts || 0);

            console.log('✅ Статистика обновлена');

        } catch (error) {
            console.error('❌ Ошибка загрузки статистики:', error);
            // Устанавливаем значения по умолчанию при ошибке
            this.updateElement('total-alerts-24h', '0');
            this.updateElement('critical-alerts-24h', '0');
            this.updateElement('resolved-alerts-24h', '0');
            this.updateElement('active-alerts', '0');
        }
    }

    async loadAlertSettings() {
        try {
            console.log('⚙️ Загрузка настроек оповещений...');
            const response = await fetch('/api/settings/alerts');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const settings = await response.json();
            console.log('Настройки получены:', settings);

            // Сохраняем исходные настройки при первой загрузке
            if (Object.keys(this.originalSettings).length === 0) {
                settings.forEach(setting => {
                    this.originalSettings[setting.metric_type] = {
                        warning: setting.warning_threshold,
                        critical: setting.critical_threshold,
                        email: setting.email_enabled,
                        escalation: setting.escalation_minutes
                    };
                });
            }

            const tableBody = document.getElementById('alert-settings-table');
            if (!tableBody) {
                console.error('Не найден элемент alert-settings-table');
                return;
            }

            tableBody.innerHTML = '';

            const metricNames = {
                'cpu': 'Процессор (%)',
                'memory': 'Память (%)',
                'disk': 'Диск (%)',
                'temperature': 'Температура (°C)',
                'humidity': 'Влажность (%)'
            };

            settings.forEach(setting => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <strong>${metricNames[setting.metric_type] || setting.metric_type}</strong>
                    </td>
                    <td>
                        <input type="number" class="form-control form-control-sm" 
                               value="${setting.warning_threshold}" 
                               data-metric="${setting.metric_type}" 
                               data-field="warning_threshold"
                               min="0" max="100" step="0.1">
                    </td>
                    <td>
                        <input type="number" class="form-control form-control-sm" 
                               value="${setting.critical_threshold}" 
                               data-metric="${setting.metric_type}" 
                               data-field="critical_threshold"
                               min="0" max="100" step="0.1">
                    </td>
                    <td>
                        <div class="form-check">
                            <input type="checkbox" class="form-check-input" 
                                   ${setting.email_enabled ? 'checked' : ''}
                                   data-metric="${setting.metric_type}" 
                                   data-field="email_enabled">
                        </div>
                    </td>
                    <td>
                        <input type="number" class="form-control form-control-sm" 
                               value="${setting.escalation_minutes}" 
                               data-metric="${setting.metric_type}" 
                               data-field="escalation_minutes"
                               min="1" max="1440">
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-secondary" 
                                    onclick="resetMetricToDefault('${setting.metric_type}')"
                                    title="Сбросить к умолчанию">
                                <i class="fas fa-undo"></i>
                            </button>
                            <button type="button" class="btn btn-outline-info" 
                                    onclick="testMetricAlert('${setting.metric_type}')"
                                    title="Тестовое оповещение">
                                <i class="fas fa-bell"></i>
                            </button>
                        </div>
                    </td>
                `;
                tableBody.appendChild(row);
            });

            // Сбрасываем флаг изменений после загрузки
            this.hasUnsavedChanges = false;
            this.updateButtonsState();

            console.log('✅ Настройки оповещений загружены');

        } catch (error) {
            console.error('❌ Ошибка загрузки настроек оповещений:', error);
        }
    }

    async loadNotificationSettings() {
        try {
            console.log('📧 Загрузка настроек уведомлений...');
            const response = await fetch('/api/settings/notifications');

            if (!response.ok) {
                console.warn('Настройки уведомлений не найдены, используем умолчания');
                return;
            }

            const settings = await response.json();

            if (settings.smtp_server) {
                this.updateInputValue('smtp-server', settings.smtp_server || '');
                this.updateInputValue('smtp-port', settings.smtp_port || 587);
                this.updateInputValue('smtp-username', settings.smtp_username || '');
                this.updateInputValue('from-email', settings.from_email || '');

                if (settings.to_emails) {
                    try {
                        const emails = JSON.parse(settings.to_emails);
                        this.updateInputValue('to-emails', emails.join(', '));
                    } catch (e) {
                        console.error('Ошибка парсинга to_emails:', e);
                    }
                }

                if (settings.admin_emails) {
                    try {
                        const adminEmails = JSON.parse(settings.admin_emails);
                        this.updateInputValue('admin-emails', adminEmails.join(', '));
                    } catch (e) {
                        console.error('Ошибка парсинга admin_emails:', e);
                    }
                }
            }

            console.log('✅ Настройки уведомлений загружены');

        } catch (error) {
            console.error('❌ Ошибка загрузки настроек уведомлений:', error);
        }
    }

    async loadActiveAlerts() {
        try {
            console.log('🚨 Загрузка активных инцидентов...');
            const limit = document.getElementById('alerts-limit')?.value || 10;
            const response = await fetch(`/api/alerts/active?limit=${limit}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const alerts = await response.json();

            const container = document.getElementById('active-alerts-container');
            if (!container) {
                console.error('Не найден элемент active-alerts-container');
                return;
            }

            if (alerts.length === 0) {
                container.innerHTML = '<p class="text-muted text-center">Нет активных инцидентов</p>';
                return;
            }

            container.innerHTML = alerts.map(alert => `
                <div class="alert alert-${alert.severity === 'critical' ? 'danger' : 'warning'} d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${alert.alert_type.toUpperCase()}</strong> - ${alert.message}
                        <br>
                        <small class="text-muted">${alert.timestamp}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-success" onclick="resolveAlert(${alert.id})">
                        <i class="fas fa-check"></i> Разрешить
                    </button>
                </div>
            `).join('');

            console.log('✅ Активные инциденты загружены');

        } catch (error) {
            console.error('❌ Ошибка загрузки активных инцидентов:', error);
            const container = document.getElementById('active-alerts-container');
            if (container) {
                container.innerHTML = '<p class="text-muted text-center">Ошибка загрузки инцидентов</p>';
            }
        }
    }

    async loadUsers() {
        try {
            console.log('👥 Загрузка пользователей...');
            const response = await fetch('/api/users');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const users = await response.json();

            const tableBody = document.getElementById('users-table');
            if (!tableBody) {
                console.error('Не найден элемент users-table');
                return;
            }

            tableBody.innerHTML = users.map(user => `
                <tr>
                    <td>
                        <strong style="color: var(--text-primary) !important;">${user.username}</strong>
                        ${user.id === 1 ? '<span class="badge bg-primary ms-2">Системный</span>' : ''}
                    </td>
                    <td style="color: var(--text-primary) !important;">${user.email}</td>
                    <td>
                        <span class="badge" style="background-color: ${this.getRoleBadgeColor(user.role)}; color: white;">
                            ${this.getRoleDisplayName(user.role)}
                        </span>
                    </td>
                    <td>
                        <span class="badge bg-${user.is_active ? 'success' : 'secondary'}">
                            ${user.is_active ? 'Активен' : 'Отключен'}
                        </span>
                    </td>
                    <td style="color: var(--text-primary) !important;">
                        ${user.last_login ? new Date(user.last_login).toLocaleString('ru-RU') : 'Никогда'}
                    </td>
                    <td>
                        ${user.id !== 1 ? `
                            <button class="btn btn-sm btn-outline-primary me-1" onclick="editUser(${user.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.id}, '${user.username}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : '<span class="text-muted">Системный пользователь</span>'}
                    </td>
                </tr>
            `).join('');

            console.log('✅ Пользователи загружены');

        } catch (error) {
            console.error('❌ Ошибка загрузки пользователей:', error);
            const tableBody = document.getElementById('users-table');
            if (tableBody) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Ошибка загрузки пользователей</td></tr>';
            }
        }
    }

    async loadAuditLogs() {
        try {
            console.log('📋 Загрузка журнала аудита...');
            const limit = document.getElementById('audit-limit')?.value || 20;
            const response = await fetch(`/api/audit-logs?per_page=${limit}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            const container = document.getElementById('audit-logs-container');
            if (!container) {
                console.error('Не найден элемент audit-logs-container');
                return;
            }

            if (data.logs && data.logs.length > 0) {
                container.innerHTML = `
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Время</th>
                                    <th>Пользователь</th>
                                    <th>Действие</th>
                                    <th>Ресурс</th>
                                    <th>Детали</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.logs.map(log => `
                                    <tr>
                                        <td>${new Date(log.timestamp).toLocaleString('ru-RU')}</td>
                                        <td>${log.username}</td>
                                        <td><span class="badge" style="background-color: #1E40AF; color: white;">${log.action}</span></td>
                                        <td>${log.resource || '-'}</td>
                                        <td>${log.details || '-'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <p class="text-muted text-center mt-3">
                        Показано ${data.logs.length} из ${data.total} записей
                        ${data.total > limit ? `(ограничено ${limit} записями)` : ''}
                    </p>
                `;
            } else {
                container.innerHTML = '<p class="text-muted text-center">Нет записей в журнале</p>';
            }

            console.log('✅ Журнал аудита загружен');

        } catch (error) {
            console.error('❌ Ошибка загрузки журнала:', error);
            const container = document.getElementById('audit-logs-container');
            if (container) {
                container.innerHTML = '<p class="text-muted text-center">Ошибка загрузки журнала аудита</p>';
            }
        }
    }

    // Переключение между режимами редактирования
    switchSettingsMode(mode) {
        this.currentMode = mode;

        const saveButtonText = document.getElementById('saveButtonText');
        const resetButtonText = document.getElementById('resetButtonText');
        const modeIndicator = document.getElementById('modeIndicator');

        if (mode === 'current') {
            saveButtonText.textContent = 'Сохранить настройки';
            resetButtonText.textContent = 'Сбросить к умолчаниям';
            modeIndicator.textContent = 'Редактируются текущие настройки';
            modeIndicator.className = 'badge bg-primary';

            // Загружаем текущие настройки
            this.loadAlertSettings();
        } else {
            saveButtonText.textContent = 'Сохранить как умолчания';
            resetButtonText.textContent = 'Сбросить к системным';
            modeIndicator.textContent = 'Редактируются настройки по умолчанию';
            modeIndicator.className = 'badge bg-success';

            // Загружаем настройки по умолчанию
            this.loadCustomDefaults();
        }
    }

    async loadCustomDefaults() {
        try {
            const response = await fetch('/api/settings/get-defaults');
            if (response.ok) {
                const settings = await response.json();
                this.customDefaults = settings;
                this.applySettingsToForm(settings);
            }
        } catch (error) {
            console.error('Ошибка загрузки настроек по умолчанию:', error);
        }
    }

    applySettingsToForm(settings) {
        const tableBody = document.getElementById('alert-settings-table');
        if (!tableBody) return;

        const rows = tableBody.querySelectorAll('tr');
        rows.forEach(row => {
            const metricInput = row.querySelector('[data-metric]');
            if (metricInput) {
                const metric = metricInput.dataset.metric;
                const setting = settings[metric];

                if (setting) {
                    row.querySelector('[data-field="warning_threshold"]').value = setting.warning || setting.warning_threshold;
                    row.querySelector('[data-field="critical_threshold"]').value = setting.critical || setting.critical_threshold;
                    row.querySelector('[data-field="email_enabled"]').checked = setting.email !== undefined ? setting.email : setting.email_enabled;
                    row.querySelector('[data-field="escalation_minutes"]').value = setting.escalation || setting.escalation_minutes;
                }
            }
        });
    }

    resetSettings() {
        if (this.currentMode === 'current') {
            // Сбрасываем текущие к настройкам по умолчанию
            if (confirm('Сбросить текущие настройки к сохраненным умолчаниям?')) {
                this.applySettingsToForm(this.customDefaults);
                this.showAlert('Настройки сброшены к умолчаниям', 'info');
            }
        } else {
            // Сбрасываем умолчания к системным
            if (confirm('Сбросить к системным умолчаниям?')) {
                const systemDefaults = {
                    'cpu': { warning: 70, critical: 85, email: true, escalation: 15 },
                    'memory': { warning: 75, critical: 90, email: true, escalation: 10 },
                    'disk': { warning: 80, critical: 90, email: true, escalation: 30 },
                    'temperature': { warning: 30, critical: 40, email: true, escalation: 5 },
                    'humidity': { warning: 65, critical: 80, email: false, escalation: 60 }
                };
                this.applySettingsToForm(systemDefaults);
                this.showAlert('Сброшено к системным умолчаниям', 'info');
            }
        }
    }

    // Сохранение настроек
    async saveAlertSettings() {
        try {
            if (this.currentMode === 'default') {
                // Сохраняем как настройки по умолчанию
                const settings = this.getCurrentSettings();

                const response = await fetch('/api/settings/save-defaults', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });

                if (response.ok) {
                    this.customDefaults = settings;
                    this.showAlert('Настройки по умолчанию обновлены!', 'success');
                } else {
                    this.showAlert('Ошибка сохранения настроек по умолчанию', 'danger');
                }
            } else {
                // Сохраняем как текущие настройки
                const settings = [];
                const tableBody = document.getElementById('alert-settings-table');
                const rows = tableBody.querySelectorAll('tr');

                rows.forEach(row => {
                    const metricInput = row.querySelector('[data-field="warning_threshold"]');
                    if (metricInput && metricInput.dataset.metric) {
                        const metric = metricInput.dataset.metric;
                        settings.push({
                            metric_type: metric,
                            warning_threshold: parseFloat(row.querySelector('[data-field="warning_threshold"]').value),
                            critical_threshold: parseFloat(row.querySelector('[data-field="critical_threshold"]').value),
                            email_enabled: row.querySelector('[data-field="email_enabled"]').checked,
                            escalation_minutes: parseInt(row.querySelector('[data-field="escalation_minutes"]').value)
                        });
                    }
                });

                const response = await fetch('/api/settings/alerts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });

                const result = await response.json();
                if (result.success) {
                    this.showAlert('Текущие настройки сохранены!', 'success');
                } else {
                    this.showAlert('Ошибка сохранения: ' + result.error, 'danger');
                }
            }
        } catch (error) {
            this.showAlert('Ошибка сохранения: ' + error.message, 'danger');
        }
    }

    async saveNotificationSettings() {
        try {
            const toEmails = document.getElementById('to-emails').value
                .split(',')
                .map(email => email.trim())
                .filter(email => email);

            const adminEmails = document.getElementById('admin-emails').value
                .split(',')
                .map(email => email.trim())
                .filter(email => email);

            const data = {
                smtp_server: document.getElementById('smtp-server').value,
                smtp_port: parseInt(document.getElementById('smtp-port').value),
                smtp_username: document.getElementById('smtp-username').value,
                from_email: document.getElementById('from-email').value,
                to_emails: toEmails,
                admin_emails: adminEmails
            };

            const password = document.getElementById('smtp-password').value;
            if (password) {
                data.smtp_password = password;
            }

            const response = await fetch('/api/settings/notifications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showAlert('Настройки email сохранены успешно!', 'success');
                document.getElementById('smtp-password').value = '';
            } else {
                this.showAlert('Ошибка сохранения настроек: ' + result.error, 'danger');
            }

        } catch (error) {
            this.showAlert('Ошибка сохранения настроек: ' + error.message, 'danger');
        }
    }

    getCurrentSettings() {
        const settings = {};
        const tableBody = document.getElementById('alert-settings-table');
        if (!tableBody) return settings;

        const rows = tableBody.querySelectorAll('tr');
        rows.forEach(row => {
            const warningInput = row.querySelector('[data-field="warning_threshold"]');
            if (warningInput && warningInput.dataset.metric) {
                const metric = warningInput.dataset.metric;
                settings[metric] = {
                    warning: parseFloat(row.querySelector('[data-field="warning_threshold"]').value),
                    critical: parseFloat(row.querySelector('[data-field="critical_threshold"]').value),
                    email: row.querySelector('[data-field="email_enabled"]').checked,
                    escalation: parseInt(row.querySelector('[data-field="escalation_minutes"]').value)
                };
            }
        });
        return settings;
    }

    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1060; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertDiv);

        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    }

    // Вспомогательные методы
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        } else {
            console.warn(`Элемент ${id} не найден`);
        }
    }

    updateInputValue(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.value = value;
        } else {
            console.warn(`Элемент ${id} не найден`);
        }
    }

    getRoleBadgeColor(role) {
        const colors = {
            'admin': '#DC3545',
            'operator': '#FFC107',
            'viewer': '#1E40AF'
        };
        return colors[role] || '#6C757D';
    }

    getRoleDisplayName(role) {
        const names = {
            'admin': 'Администратор',
            'operator': 'Оператор',
            'viewer': 'Наблюдатель'
        };
        return names[role] || role;
    }

    updateButtonsState() {
        // Здесь можно добавить логику обновления состояния кнопок
        console.log('Состояние кнопок обновлено');
    }
}

// Глобальные функции
function updateAlertsLimit() {
    if (window.adminPanel) {
        window.adminPanel.loadActiveAlerts();
    }
}

function updateAuditLimit() {
    if (window.adminPanel) {
        window.adminPanel.loadAuditLogs();
    }
}

function refreshAlerts() {
    if (window.adminPanel) {
        window.adminPanel.loadActiveAlerts();
        window.adminPanel.loadStats();
    }
}

async function resolveAlert(alertId) {
    try {
        const response = await fetch(`/api/alerts/resolve/${alertId}`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success && window.adminPanel) {
            window.adminPanel.loadActiveAlerts();
            window.adminPanel.loadStats();
        }

    } catch (error) {
        console.error('Ошибка разрешения инцидента:', error);
    }
}

function resetMetricToDefault(metricType) {
    const modal = new bootstrap.Modal(document.getElementById('confirmResetModal'));
    document.getElementById('reset-metric-name').textContent = metricType;

    document.getElementById('confirm-reset-btn').onclick = () => {
        if (window.adminPanel) {
            const tableBody = document.getElementById('alert-settings-table');
            const row = Array.from(tableBody.querySelectorAll('tr')).find(r =>
                r.querySelector(`[data-metric="${metricType}"]`)
            );

            if (row) {
                const defaults = window.adminPanel.defaultSettings[metricType];
                if (defaults) {
                    row.querySelector('[data-field="warning_threshold"]').value = defaults.warning;
                    row.querySelector('[data-field="critical_threshold"]').value = defaults.critical;
                    row.querySelector('[data-field="email_enabled"]').checked = defaults.email;
                    row.querySelector('[data-field="escalation_minutes"]').value = defaults.escalation;

                    window.adminPanel.showAlert(`Настройки ${metricType} сброшены к умолчанию`, 'info');
                }
            }
        }
        modal.hide();
    };

    modal.show();
}

function testMetricAlert(metricType) {
    alert(`Тестовое оповещение для ${metricType} отправлено`);
}

function showCreateUserModal() {
    const modal = new bootstrap.Modal(document.getElementById('createUserModal'));
    modal.show();
}

async function createUser() {
    try {
        const form = document.getElementById('createUserForm');
        const formData = new FormData(form);

        const data = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            role: formData.get('role'),
            is_active: formData.has('is_active')
        };

        const response = await fetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
            form.reset();
            if (window.adminPanel) {
                window.adminPanel.loadUsers();
            }
            alert('Пользователь создан успешно!');
        } else {
            alert('Ошибка создания пользователя: ' + result.error);
        }

    } catch (error) {
        alert('Ошибка создания пользователя: ' + error.message);
    }
}

function editUser(userId) {
    // Получаем данные пользователя
    fetch('/api/users')
        .then(response => response.json())
        .then(users => {
            const user = users.find(u => u.id === userId);
            if (user) {
                // Очищаем форму
                const form = document.getElementById('createUserForm');
                form.reset();

                // Заполняем форму данными пользователя
                form.querySelector('[name="username"]').value = user.username;
                form.querySelector('[name="email"]').value = user.email;
                form.querySelector('[name="role"]').value = user.role;
                form.querySelector('[name="is_active"]').checked = user.is_active;

                // Скрываем поле пароля при редактировании
                const passwordField = form.querySelector('[name="password"]');
                const passwordContainer = passwordField.closest('.mb-3');
                passwordContainer.style.display = 'none';
                passwordField.required = false;

                // Меняем заголовок модального окна
                document.querySelector('#createUserModal .modal-title').textContent = 'Редактировать пользователя';

                // Меняем кнопку на "Обновить"
                const submitButton = document.querySelector('#createUserModal [onclick*="createUser"]');
                submitButton.textContent = 'Обновить';
                submitButton.setAttribute('onclick', `updateUser(${userId})`);

                // Показываем модальное окно
                const modal = new bootstrap.Modal(document.getElementById('createUserModal'));
                modal.show();
            }
        })
        .catch(error => {
            console.error('Ошибка получения данных пользователя:', error);
            alert('Ошибка получения данных пользователя');
        });
}

async function updateUser(userId) {
    try {
        const form = document.getElementById('createUserForm');
        const formData = new FormData(form);

        const data = {
            username: formData.get('username'),
            email: formData.get('email'),
            role: formData.get('role'),
            is_active: formData.has('is_active')
        };

        const response = await fetch(`/api/users/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            // Закрываем модальное окно
            bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();

            // Сбрасываем форму к исходному состоянию
            resetCreateUserModal();

            // Обновляем список пользователей
            if (window.adminPanel) {
                window.adminPanel.loadUsers();
            }

            alert('Пользователь обновлен успешно!');
        } else {
            alert('Ошибка обновления пользователя: ' + result.error);
        }

    } catch (error) {
        alert('Ошибка обновления пользователя: ' + error.message);
    }
}

function resetCreateUserModal() {
    // Сбрасываем заголовок
    document.querySelector('#createUserModal .modal-title').textContent = 'Добавить пользователя';

    // Показываем поле пароля
    const form = document.getElementById('createUserForm');
    const passwordField = form.querySelector('[name="password"]');
    const passwordContainer = passwordField.closest('.mb-3');
    passwordContainer.style.display = 'block';
    passwordField.required = true;

    // Сбрасываем кнопку
    const submitButton = document.querySelector('#createUserModal [onclick*="User"]');
    submitButton.textContent = 'Создать';
    submitButton.setAttribute('onclick', 'createUser()');

    // Очищаем форму
    form.reset();
}

// Добавляем обработчик закрытия модального окна
document.addEventListener('DOMContentLoaded', function() {
    const createUserModal = document.getElementById('createUserModal');
    if (createUserModal) {
        createUserModal.addEventListener('hidden.bs.modal', function () {
            resetCreateUserModal();
        });
    }
});

async function deleteUser(userId, username) {
    if (!confirm(`Удалить пользователя "${username}"?`)) return;

    try {
        const response = await fetch(`/api/users/${userId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            if (window.adminPanel) {
                window.adminPanel.loadUsers();
            }
            alert('Пользователь удален');
        } else {
            alert('Ошибка удаления: ' + result.error);
        }

    } catch (error) {
        alert('Ошибка удаления: ' + error.message);
    }
}

async function testEmail() {
    try {
        const response = await fetch('/api/test-email', {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            alert('Тестовое письмо отправлено успешно!');
        } else {
            alert('Ошибка отправки: ' + result.error);
        }

    } catch (error) {
        alert('Ошибка отправки: ' + error.message);
    }
}

// Глобальные функции для переключателя режимов
function switchSettingsMode(mode) {
    if (window.adminPanel) {
        window.adminPanel.switchSettingsMode(mode);
    }
}

function resetSettings() {
    if (window.adminPanel) {
        window.adminPanel.resetSettings();
    }
}

// Функции управления системой
async function createBackup() {
    showSystemOperation('Создание резервной копии...');
    try {
        const response = await fetch('/api/system/backup', { method: 'POST' });
        const result = await response.json();

        if (result.success) {
            showSystemOperationResult(`
                <div class="alert alert-success">
                    <h6>Резервная копия создана успешно!</h6>
                    <p>Файл: ${result.backup_name}</p>
                    <p>Размер: ${(result.size / 1024 / 1024).toFixed(2)} МБ</p>
                </div>
            `);
        } else {
            showSystemOperationResult(`<div class="alert alert-danger">Ошибка: ${result.error}</div>`);
        }
    } catch (error) {
        showSystemOperationResult(`<div class="alert alert-danger">Ошибка: ${error.message}</div>`);
    }
}

async function exportConfig() {
    showSystemOperation('Экспорт конфигурации...');
    try {
        const response = await fetch('/api/system/export-config');
        const config = await response.json();

        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `config_${new Date().toISOString().split('T')[0]}.json`;
        a.click();

        showSystemOperationResult(`<div class="alert alert-success">Конфигурация экспортирована успешно!</div>`);
    } catch (error) {
        showSystemOperationResult(`<div class="alert alert-danger">Ошибка: ${error.message}</div>`);
    }
}

async function checkSystemHealth() {
    showSystemOperation('Проверка состояния системы...');
    try {
        const response = await fetch('/api/system/health');
        const health = await response.json();

        const statusColor = health.overall_status === 'healthy' ? 'success' : 'warning';

        const checksHtml = health.checks.map(check => `
            <div class="d-flex justify-content-between align-items-center border-bottom pb-2 mb-2">
                <span>${check.name}</span>
                <span class="badge bg-${check.status === 'OK' ? 'success' : check.status === 'WARNING' ? 'warning' : 'danger'}">
                    ${check.status}
                </span>
            </div>
            <small class="text-muted">${check.message}</small>
        `).join('');

        showSystemOperationResult(`
            <div class="alert alert-${statusColor}">
                <h6>Состояние системы: ${health.overall_status}</h6>
                <small>Проверено: ${health.timestamp}</small>
            </div>
            <div>${checksHtml}</div>
        `);
    } catch (error) {
        showSystemOperationResult(`<div class="alert alert-danger">Ошибка: ${error.message}</div>`);
    }
}

async function cleanupOldData() {
    if (!confirm('Удалить данные старше 30 дней?')) return;

    showSystemOperation('Очистка старых данных...');
    try {
        const response = await fetch('/api/system/cleanup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ retention_days: 30 })
        });
        const result = await response.json();

        if (result.success) {
            showSystemOperationResult(`
                <div class="alert alert-success">
                    <h6>Очистка завершена успешно!</h6>
                    <p>Удалено метрик: ${result.cleaned.metrics}</p>
                    <p>Удалено логов аудита: ${result.cleaned.audit_logs}</p>
                    <p>Удалено оповещений: ${result.cleaned.resolved_alerts}</p>
                </div>
            `);
        } else {
            showSystemOperationResult(`<div class="alert alert-danger">Ошибка: ${result.error}</div>`);
        }
    } catch (error) {
        showSystemOperationResult(`<div class="alert alert-danger">Ошибка: ${error.message}</div>`);
    }
}

async function showSystemStats() {
    showSystemOperation('Загрузка статистики системы...');
    try {
        const response = await fetch('/api/system/statistics');
        const stats = await response.json();

        showSystemOperationResult(`
            <div class="row">
                <div class="col-md-6">
                    <h6>База данных</h6>
                    <ul>
                        <li>Всего метрик: ${stats.database?.total_metrics || 0}</li>
                        <li>Всего оповещений: ${stats.database?.total_alerts || 0}</li>
                        <li>Активных оповещений: ${stats.database?.active_alerts || 0}</li>
                        <li>Пользователей: ${stats.database?.total_users || 0}</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h6>За последние 24 часа</h6>
                    <ul>
                        <li>Собрано метрик: ${stats.last_24h?.metrics_collected || 0}</li>
                        <li>Создано оповещений: ${stats.last_24h?.alerts_generated || 0}</li>
                        <li>Входов в систему: ${stats.last_24h?.user_logins || 0}</li>
                    </ul>
                </div>
            </div>
        `);
    } catch (error) {
        showSystemOperationResult(`<div class="alert alert-danger">Ошибка: ${error.message}</div>`);
    }
}

async function showBackgroundStatus() {
    showSystemOperation('Проверка фоновых служб...');
    try {
        const response = await fetch('/api/system/background-status');
        const status = await response.json();

        showSystemOperationResult(`
            <div class="alert alert-${status.monitoring_active ? 'success' : 'warning'}">
                <h6>Мониторинг: ${status.monitoring_active ? 'Активен' : 'Неактивен'}</h6>
                ${status.last_data_time ? `<p>Последние данные: ${status.last_data_time}</p>` : ''}
                ${status.seconds_since_last ? `<p>Секунд назад: ${status.seconds_since_last}</p>` : ''}
                <p>Всего метрик в БД: ${status.total_metrics_count}</p>
            </div>
        `);
    } catch (error) {
        showSystemOperationResult(`<div class="alert alert-danger">Ошибка: ${error.message}</div>`);
    }
}

function showSystemOperation(message) {
    const container = document.getElementById('system-operation-results');
    const content = document.getElementById('operation-content');

    content.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2">${message}</p>
        </div>
    `;

    container.style.display = 'block';
}

function showSystemOperationResult(html) {
    const content = document.getElementById('operation-content');
    content.innerHTML = html;
}

// Инициализация при загрузке страницы
console.log('🔄 Начало инициализации админки...');
window.adminPanel = new AdminPanel();