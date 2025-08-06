/**
 * AI DevOps Assistant Dashboard JavaScript
 */

class Dashboard {
    constructor() {
        this.currentTheme = 'light';
        this.currentLanguage = 'en';
        this.monitoringActive = false;
        this.exchangeData = {};
        this.priceChart = null;
        
        this.translations = {
            en: {
                overview: 'Overview',
                exchanges: 'Exchanges',
                monitoring: 'Monitoring',
                analysis: 'Code Analysis',
                workflows: 'Workflows',
                reports: 'Reports',
                key_metrics: 'Key Metrics',
                connected_exchanges: 'Connected Exchanges',
                active_workflows: 'Active Workflows',
                avg_response_time: 'Avg Response Time',
                active_alerts: 'Active Alerts',
                price_trends: 'Price Trends',
                exchange_status: 'Exchange Status',
                recent_activity: 'Recent Activity',
                cryptocurrency_exchanges: 'Cryptocurrency Exchanges',
                refresh: 'Refresh',
                real_time_monitoring: 'Real-time Monitoring',
                start: 'Start',
                stop: 'Stop',
                price_alerts: 'Price Alerts',
                system_health: 'System Health',
                code_analysis: 'AI Code Analysis',
                run_analysis: 'Run Analysis',
                no_analysis_results: 'No analysis results yet. Run an analysis to see results here.',
                github_workflows: 'GitHub Workflows',
                load: 'Load',
                no_workflows: 'Enter a repository name to load workflows.',
                daily: 'Daily',
                weekly: 'Weekly',
                monthly: 'Monthly',
                generate: 'Generate',
                no_reports: 'No reports generated yet.',
                loading: 'Loading...',
                connected: 'Connected',
                disconnected: 'Disconnected',
                error: 'Error'
            },
            fa: {
                overview: 'نمای کلی',
                exchanges: 'صرافی‌ها',
                monitoring: 'نظارت',
                analysis: 'تحلیل کد',
                workflows: 'جریان کاری',
                reports: 'گزارشات',
                key_metrics: 'معیارهای کلیدی',
                connected_exchanges: 'صرافی‌های متصل',
                active_workflows: 'جریان‌های کاری فعال',
                avg_response_time: 'متوسط زمان پاسخ',
                active_alerts: 'هشدارهای فعال',
                price_trends: 'روند قیمت‌ها',
                exchange_status: 'وضعیت صرافی‌ها',
                recent_activity: 'فعالیت‌های اخیر',
                cryptocurrency_exchanges: 'صرافی‌های رمزارز',
                refresh: 'به‌روزرسانی',
                real_time_monitoring: 'نظارت لحظه‌ای',
                start: 'شروع',
                stop: 'توقف',
                price_alerts: 'هشدارهای قیمت',
                system_health: 'سلامت سیستم',
                code_analysis: 'تحلیل کد هوشمند',
                run_analysis: 'اجرای تحلیل',
                no_analysis_results: 'هنوز نتیجه تحلیلی وجود ندارد. برای مشاهده نتایج، تحلیل را اجرا کنید.',
                github_workflows: 'جریان‌های کاری گیت‌هاب',
                load: 'بارگذاری',
                no_workflows: 'نام مخزن را وارد کنید تا جریان‌های کاری بارگذاری شوند.',
                daily: 'روزانه',
                weekly: 'هفتگی',
                monthly: 'ماهانه',
                generate: 'تولید',
                no_reports: 'هنوز گزارشی تولید نشده است.',
                loading: 'در حال بارگذاری...',
                connected: 'متصل',
                disconnected: 'قطع شده',
                error: 'خطا'
            }
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.loadInitialData();
        this.setupAutoRefresh();
    }
    
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });
        
        // Theme toggle
        window.toggleTheme = () => this.toggleTheme();
        window.toggleLanguage = () => this.toggleLanguage();
        
        // Exchange functions
        window.refreshExchanges = () => this.refreshExchanges();
        
        // Monitoring functions
        window.startMonitoring = () => this.startMonitoring();
        window.stopMonitoring = () => this.stopMonitoring();
        
        // Analysis functions
        window.runAnalysis = () => this.runAnalysis();
        
        // Workflow functions
        window.loadWorkflows = () => this.loadWorkflows();
        
        // Report functions
        window.generateReport = () => this.generateReport();
    }
    
    switchTab(tabName) {
        // Update tab navigation
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === tabName);
        });
        
        // Load tab-specific data
        this.loadTabData(tabName);
    }
    
    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', this.currentTheme);
        
        const themeIcon = document.querySelector('.theme-toggle i');
        themeIcon.className = this.currentTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        
        localStorage.setItem('dashboard-theme', this.currentTheme);
    }
    
    toggleLanguage() {
        this.currentLanguage = this.currentLanguage === 'en' ? 'fa' : 'en';
        document.getElementById('lang-text').textContent = this.currentLanguage.toUpperCase();
        
        // Set RTL for Persian
        if (this.currentLanguage === 'fa') {
            document.documentElement.setAttribute('dir', 'rtl');
        } else {
            document.documentElement.removeAttribute('dir');
        }
        
        this.updateLanguage();
        localStorage.setItem('dashboard-language', this.currentLanguage);
    }
    
    updateLanguage() {
        const translations = this.translations[this.currentLanguage];
        
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (translations[key]) {
                element.textContent = translations[key];
            }
        });
        
        // Update option texts
        document.querySelectorAll('option[data-i18n]').forEach(option => {
            const key = option.getAttribute('data-i18n');
            if (translations[key]) {
                option.textContent = translations[key];
            }
        });
    }
    
    initializeCharts() {
        const ctx = document.getElementById('price-chart').getContext('2d');
        
        this.priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Price',
                    data: [],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
        
        // Price symbol change handler
        document.getElementById('price-symbol').addEventListener('change', (e) => {
            this.updatePriceChart(e.target.value);
        });
    }
    
    async loadInitialData() {
        await this.loadExchangeStatus();
        await this.loadMetrics();
        await this.loadRecentActivity();
    }
    
    setupAutoRefresh() {
        // Refresh data every 30 seconds
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.loadInitialData();
            }
        }, 30000);
    }
    
    async loadTabData(tabName) {
        switch (tabName) {
            case 'exchanges':
                await this.loadExchanges();
                break;
            case 'monitoring':
                await this.loadMonitoring();
                break;
            case 'analysis':
                await this.loadAnalysisResults();
                break;
            case 'workflows':
                await this.loadWorkflows();
                break;
            case 'reports':
                await this.loadReports();
                break;
        }
    }
    
    async apiRequest(endpoint, options = {}) {
        try {
            const response = await fetch(`/api${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);
            return null;
        }
    }
    
    async loadMetrics() {
        const data = await this.apiRequest('/metrics');
        
        if (data) {
            document.getElementById('connected-exchanges').textContent = data.connected_exchanges || 0;
            document.getElementById('active-workflows').textContent = data.active_workflows || 0;
            document.getElementById('avg-response-time').textContent = `${data.avg_response_time_ms || 0}ms`;
            document.getElementById('active-alerts').textContent = data.active_alerts || 0;
        }
    }
    
    async loadExchangeStatus() {
        const data = await this.apiRequest('/exchanges/status');
        const container = document.getElementById('exchange-status-list');
        
        if (data && data.exchanges) {
            container.innerHTML = data.exchanges.map(exchange => `
                <div class="exchange-item">
                    <div class="exchange-info">
                        <div class="exchange-logo">
                            ${exchange.name.charAt(0).toUpperCase()}
                        </div>
                        <div class="exchange-details">
                            <h4>${exchange.display_name || exchange.name}</h4>
                            <p>${exchange.type === 'iranian' ? 'صرافی ایرانی' : 'International Exchange'}</p>
                        </div>
                    </div>
                    <span class="status-badge ${exchange.connected ? 'status-connected' : 'status-disconnected'}">
                        ${exchange.connected ? this.translations[this.currentLanguage].connected : this.translations[this.currentLanguage].disconnected}
                    </span>
                </div>
            `).join('');
        }
    }
    
    async loadRecentActivity() {
        const data = await this.apiRequest('/activity');
        const container = document.getElementById('activity-list');
        
        if (data && data.activities) {
            container.innerHTML = data.activities.map(activity => `
                <div class="activity-item">
                    <div class="activity-icon">
                        <i class="${activity.icon || 'fas fa-info'}"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">${activity.title}</div>
                        <div class="activity-time">${new Date(activity.timestamp).toLocaleString()}</div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="activity-item">
                    <div class="activity-icon">
                        <i class="fas fa-info"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">Dashboard Started</div>
                        <div class="activity-time">${new Date().toLocaleString()}</div>
                    </div>
                </div>
            `;
        }
    }
    
    async updatePriceChart(symbol) {
        const data = await this.apiRequest(`/prices/${symbol}`);
        
        if (data && data.prices) {
            this.priceChart.data.labels = data.prices.map(p => new Date(p.timestamp).toLocaleTimeString());
            this.priceChart.data.datasets[0].data = data.prices.map(p => p.price);
            this.priceChart.update();
        }
    }
    
    async refreshExchanges() {
        this.showLoading();
        await this.loadExchanges();
        this.hideLoading();
    }
    
    async loadExchanges() {
        const data = await this.apiRequest('/exchanges');
        const container = document.getElementById('exchanges-grid');
        
        if (data && data.exchanges) {
            container.innerHTML = data.exchanges.map(exchange => `
                <div class="card exchange-card">
                    <div class="card-header">
                        <div class="exchange-header">
                            <div>
                                <h3>${exchange.display_name || exchange.name}</h3>
                                <p>${exchange.type === 'iranian' ? 'صرافی ایرانی' : 'International Exchange'}</p>
                            </div>
                            <span class="status-badge ${exchange.connected ? 'status-connected' : 'status-disconnected'}">
                                ${exchange.connected ? this.translations[this.currentLanguage].connected : this.translations[this.currentLanguage].disconnected}
                            </span>
                        </div>
                    </div>
                    <div class="card-content">
                        <div class="exchange-stats">
                            <div class="stat">
                                <div class="stat-value">${exchange.response_time_ms || 0}ms</div>
                                <div class="stat-label">Response Time</div>
                            </div>
                            <div class="stat">
                                <div class="stat-value">${exchange.error_count || 0}</div>
                                <div class="stat-label">Errors</div>
                            </div>
                        </div>
                        ${exchange.features ? `
                            <div class="exchange-features">
                                <h4>Features:</h4>
                                <ul>
                                    ${exchange.features.map(feature => `<li>${feature}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('');
        }
    }
    
    async startMonitoring() {
        const result = await this.apiRequest('/monitoring/start', { method: 'POST' });
        
        if (result && result.success) {
            this.monitoringActive = true;
            document.getElementById('start-monitoring').disabled = true;
            document.getElementById('stop-monitoring').disabled = false;
            
            this.updateConnectionStatus('monitoring', 'Monitoring Active');
        }
    }
    
    async stopMonitoring() {
        const result = await this.apiRequest('/monitoring/stop', { method: 'POST' });
        
        if (result && result.success) {
            this.monitoringActive = false;
            document.getElementById('start-monitoring').disabled = false;
            document.getElementById('stop-monitoring').disabled = true;
            
            this.updateConnectionStatus('connected', 'Connected');
        }
    }
    
    async loadMonitoring() {
        const alertsData = await this.apiRequest('/monitoring/alerts');
        const healthData = await this.apiRequest('/monitoring/health');
        
        // Load price alerts
        const alertsContainer = document.getElementById('price-alerts');
        if (alertsData && alertsData.alerts) {
            alertsContainer.innerHTML = alertsData.alerts.map(alert => `
                <div class="alert-item ${alert.severity === 'critical' ? 'alert-critical' : alert.severity === 'warning' ? 'alert-warning' : 'alert-info'}">
                    <div>
                        <strong>${alert.symbol}</strong> on ${alert.exchange}
                        <br>
                        <small>${alert.message}</small>
                    </div>
                    <div>
                        ${alert.change}%
                    </div>
                </div>
            `).join('');
        } else {
            alertsContainer.innerHTML = '<p>No active price alerts</p>';
        }
        
        // Load system health
        const healthContainer = document.getElementById('system-health');
        if (healthData && healthData.metrics) {
            healthContainer.innerHTML = Object.entries(healthData.metrics).map(([key, value]) => `
                <div class="health-metric">
                    <span>${key.replace('_', ' ').toUpperCase()}</span>
                    <span class="health-value ${value.status === 'good' ? 'health-good' : value.status === 'warning' ? 'health-warning' : 'health-critical'}">
                        ${value.value}
                    </span>
                </div>
            `).join('');
        }
    }
    
    async runAnalysis() {
        this.showLoading();
        
        const result = await this.apiRequest('/analysis/run', { method: 'POST' });
        
        if (result && result.success) {
            await this.loadAnalysisResults();
        }
        
        this.hideLoading();
    }
    
    async loadAnalysisResults() {
        const data = await this.apiRequest('/analysis/results');
        const container = document.getElementById('analysis-results');
        
        if (data && data.results && data.results.length > 0) {
            container.innerHTML = data.results.map(result => `
                <div class="card">
                    <div class="card-header">
                        <h3>${result.repository || 'Analysis Result'}</h3>
                        <span class="status-badge ${result.status === 'completed' ? 'status-connected' : 'status-disconnected'}">
                            ${result.status}
                        </span>
                    </div>
                    <div class="card-content">
                        <p><strong>Model:</strong> ${result.model}</p>
                        <p><strong>Exchanges:</strong> ${result.exchanges.join(', ') || 'None'}</p>
                        <p><strong>Summary:</strong> ${result.summary}</p>
                        ${result.issues ? `
                            <div class="analysis-issues">
                                <h4>Issues Found:</h4>
                                <ul>
                                    ${result.issues.map(issue => `<li>${issue}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-code"></i>
                    <p data-i18n="no_analysis_results">No analysis results yet. Run an analysis to see results here.</p>
                </div>
            `;
        }
    }
    
    async loadWorkflows() {
        const repository = document.getElementById('repository-input').value;
        
        if (!repository) {
            alert('Please enter a repository name (owner/repo)');
            return;
        }
        
        this.showLoading();
        
        const data = await this.apiRequest(`/workflows/${repository}`);
        const container = document.getElementById('workflows-list');
        
        if (data && data.workflows) {
            container.innerHTML = data.workflows.map(workflow => `
                <div class="card">
                    <div class="card-header">
                        <h3>${workflow.name}</h3>
                        <span class="status-badge ${workflow.status === 'success' ? 'status-connected' : workflow.status === 'failure' ? 'status-disconnected' : 'status-warning'}">
                            ${workflow.status}
                        </span>
                    </div>
                    <div class="card-content">
                        <p><strong>Branch:</strong> ${workflow.branch}</p>
                        <p><strong>Last Run:</strong> ${new Date(workflow.updated_at).toLocaleString()}</p>
                        <p><strong>Duration:</strong> ${workflow.duration || 'N/A'}</p>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fab fa-github"></i>
                    <p>No workflows found for ${repository}</p>
                </div>
            `;
        }
        
        this.hideLoading();
    }
    
    async generateReport() {
        const period = document.getElementById('report-period').value;
        const format = document.getElementById('report-format').value;
        
        this.showLoading();
        
        const result = await this.apiRequest('/reports/generate', {
            method: 'POST',
            body: JSON.stringify({ period, format })
        });
        
        if (result && result.success) {
            await this.loadReports();
        }
        
        this.hideLoading();
    }
    
    async loadReports() {
        const data = await this.apiRequest('/reports');
        const container = document.getElementById('reports-list');
        
        if (data && data.reports && data.reports.length > 0) {
            container.innerHTML = data.reports.map(report => `
                <div class="card">
                    <div class="card-header">
                        <h3>${report.type.replace('_', ' ').toUpperCase()}</h3>
                        <a href="${report.download_url}" class="btn btn-primary" download>
                            <i class="fas fa-download"></i>
                            Download
                        </a>
                    </div>
                    <div class="card-content">
                        <p><strong>Generated:</strong> ${new Date(report.generated_at).toLocaleString()}</p>
                        <p><strong>Format:</strong> ${report.format.toUpperCase()}</p>
                        <p><strong>Size:</strong> ${report.size || 'N/A'}</p>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-chart-bar"></i>
                    <p data-i18n="no_reports">No reports generated yet.</p>
                </div>
            `;
        }
    }
    
    updateConnectionStatus(status, text) {
        const indicator = document.getElementById('connection-status');
        const icon = indicator.querySelector('i');
        const span = indicator.querySelector('span');
        
        indicator.className = `status-indicator status-${status}`;
        span.textContent = text;
        
        if (status === 'connected') {
            icon.className = 'fas fa-circle';
        } else if (status === 'monitoring') {
            icon.className = 'fas fa-pulse';
        } else {
            icon.className = 'fas fa-circle';
        }
    }
    
    showLoading() {
        document.getElementById('loading-overlay').style.display = 'flex';
    }
    
    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
    
    // Load saved preferences
    const savedTheme = localStorage.getItem('dashboard-theme');
    const savedLanguage = localStorage.getItem('dashboard-language');
    
    if (savedTheme && savedTheme !== 'light') {
        window.dashboard.toggleTheme();
    }
    
    if (savedLanguage && savedLanguage !== 'en') {
        window.dashboard.toggleLanguage();
    }
});