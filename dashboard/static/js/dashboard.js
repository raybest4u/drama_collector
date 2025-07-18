// dashboard/static/js/dashboard.js

class DashboardApp {
    constructor() {
        this.apiBase = 'http://localhost:8000';
        this.currentSection = 'overview';
        this.refreshInterval = null;
        this.refreshRate = 5000; // 5 seconds
        this.isRefreshing = false;
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        this.showSection('overview');
        await this.loadInitialData();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const section = btn.dataset.section;
                this.showSection(section);
            });
        });
        
        // Control buttons
        document.getElementById('start-orchestrator')?.addEventListener('click', () => {
            this.startOrchestrator();
        });
        
        document.getElementById('stop-orchestrator')?.addEventListener('click', () => {
            this.stopOrchestrator();
        });
        
        document.getElementById('start-job')?.addEventListener('click', () => {
            this.startCollectionJob();
        });
        
        document.getElementById('export-data')?.addEventListener('click', () => {
            this.exportData();
        });
        
        document.getElementById('refresh-data')?.addEventListener('click', () => {
            this.refreshAllData();
        });
        
        // Forms
        document.getElementById('job-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitJobForm();
        });
        
        document.getElementById('export-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitExportForm();
        });
        
        // Auto-refresh toggle
        document.getElementById('auto-refresh')?.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });
    }
    
    showSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionName}"]`)?.classList.add('active');
        
        // Update content
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`${sectionName}-section`)?.classList.add('active');
        
        this.currentSection = sectionName;
        
        // Load section-specific data
        this.loadSectionData(sectionName);
    }
    
    async loadSectionData(section) {
        switch (section) {
            case 'overview':
                await Promise.all([
                    this.loadSystemStatus(),
                    this.loadCurrentJob(),
                    this.loadRecentJobs()
                ]);
                break;
            case 'jobs':
                await Promise.all([
                    this.loadCurrentJob(),
                    this.loadJobHistory()
                ]);
                break;
            case 'data':
                await Promise.all([
                    this.loadDramaList(),
                    this.loadExportStats()
                ]);
                break;
            case 'config':
                await this.loadConfiguration();
                break;
            case 'monitoring':
                await Promise.all([
                    this.loadPerformanceStats(),
                    this.loadSystemHealth()
                ]);
                break;
        }
    }
    
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadSystemStatus(),
                this.loadCurrentJob()
            ]);
        } catch (error) {
            this.showAlert('error', `Failed to load initial data: ${error.message}`);
        }
    }
    
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.apiBase}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API call failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    async loadSystemStatus() {
        try {
            const data = await this.apiCall('/status');
            this.updateSystemStatus(data);
        } catch (error) {
            this.updateSystemStatus(null, error);
        }
    }
    
    updateSystemStatus(data, error = null) {
        if (error) {
            document.getElementById('system-status').textContent = 'Error';
            document.getElementById('system-indicator').className = 'status-indicator status-error';
            return;
        }
        
        const orchestratorState = data.orchestrator.state;
        document.getElementById('system-status').textContent = orchestratorState;
        
        const indicator = document.getElementById('system-indicator');
        indicator.className = `status-indicator ${this.getStatusClass(orchestratorState)}`;
        
        // Update other status cards
        document.getElementById('components-status').textContent = 
            data.components.orchestrator_initialized ? 'Initialized' : 'Not Ready';
        document.getElementById('total-jobs').textContent = data.orchestrator.total_jobs || 0;
        document.getElementById('successful-jobs').textContent = data.orchestrator.successful_jobs || 0;
        document.getElementById('failed-jobs').textContent = data.orchestrator.failed_jobs || 0;
        
        // Update last updated timestamp
        document.getElementById('last-updated').textContent = 
            new Date().toLocaleTimeString();
    }
    
    getStatusClass(status) {
        const statusMap = {
            'idle': 'status-idle',
            'collecting': 'status-warning',
            'processing': 'status-warning',
            'storing': 'status-warning',
            'exporting': 'status-warning',
            'completed': 'status-healthy',
            'error': 'status-error',
            'stopped': 'status-error'
        };
        return statusMap[status] || 'status-idle';
    }
    
    async loadCurrentJob() {
        try {
            const data = await this.apiCall('/jobs/current');
            this.updateCurrentJob(data);
        } catch (error) {
            this.updateCurrentJob(null, error);
        }
    }
    
    updateCurrentJob(data, error = null) {
        const container = document.getElementById('current-job-info');
        
        if (error || !data || data.message) {
            container.innerHTML = '<p>No active job</p>';
            return;
        }
        
        const startTime = new Date(data.start_time).toLocaleString();
        const duration = data.end_time ? 
            Math.round((new Date(data.end_time) - new Date(data.start_time)) / 1000) + 's' :
            Math.round((Date.now() - new Date(data.start_time)) / 1000) + 's';
        
        container.innerHTML = `
            <div class="job-info">
                <h4>${data.job_id}</h4>
                <p><span class="job-status ${data.state}">${data.state}</span></p>
                <p><strong>Started:</strong> ${startTime}</p>
                <p><strong>Duration:</strong> ${duration}</p>
                <p><strong>Collected:</strong> ${data.total_collected}</p>
                <p><strong>Processed:</strong> ${data.total_processed}</p>
                <p><strong>Stored:</strong> ${data.total_stored}</p>
                ${data.errors.length > 0 ? `<p><strong>Errors:</strong> ${data.errors.length}</p>` : ''}
            </div>
        `;
    }
    
    async loadJobHistory() {
        try {
            const data = await this.apiCall('/jobs/history?limit=20');
            this.updateJobHistory(data);
        } catch (error) {
            this.showAlert('error', `Failed to load job history: ${error.message}`);
        }
    }
    
    updateJobHistory(jobs) {
        const tbody = document.querySelector('#job-history-table tbody');
        if (!tbody) return;
        
        tbody.innerHTML = jobs.map(job => {
            const startTime = new Date(job.start_time).toLocaleString();
            const duration = job.end_time ? 
                Math.round((new Date(job.end_time) - new Date(job.start_time)) / 1000) + 's' :
                'Running';
            
            return `
                <tr>
                    <td>${job.job_id}</td>
                    <td><span class="job-status ${job.state}">${job.state}</span></td>
                    <td>${startTime}</td>
                    <td>${duration}</td>
                    <td>${job.total_collected}</td>
                    <td>${job.total_processed}</td>
                    <td>${job.total_stored}</td>
                    <td>${job.errors_count}</td>
                </tr>
            `;
        }).join('');
    }
    
    async loadRecentJobs() {
        try {
            const data = await this.apiCall('/jobs/history?limit=5');
            this.updateRecentJobs(data);
        } catch (error) {
            console.error('Failed to load recent jobs:', error);
        }
    }
    
    updateRecentJobs(jobs) {
        const container = document.getElementById('recent-jobs');
        if (!container) return;
        
        if (jobs.length === 0) {
            container.innerHTML = '<p>No recent jobs</p>';
            return;
        }
        
        container.innerHTML = jobs.map(job => `
            <div class="recent-job">
                <strong>${job.job_id}</strong>
                <span class="job-status ${job.state}">${job.state}</span>
                <small>${new Date(job.start_time).toLocaleString()}</small>
            </div>
        `).join('');
    }
    
    async loadDramaList() {
        try {
            const data = await this.apiCall('/dramas?limit=50');
            this.updateDramaList(data);
        } catch (error) {
            this.showAlert('error', `Failed to load drama list: ${error.message}`);
        }
    }
    
    updateDramaList(dramas) {
        const tbody = document.querySelector('#drama-list-table tbody');
        if (!tbody) return;
        
        tbody.innerHTML = dramas.map(drama => `
            <tr>
                <td>${drama.title || 'N/A'}</td>
                <td>${drama.year || 'N/A'}</td>
                <td>${drama.rating || 'N/A'}</td>
                <td>${Array.isArray(drama.genre) ? drama.genre.join(', ') : drama.genre || 'N/A'}</td>
                <td>${drama.data_source || 'N/A'}</td>
                <td>${drama.quality_score || 'N/A'}</td>
                <td>
                    <button class="btn btn-small" onclick="dashboard.viewDramaDetail('${drama.id}')">
                        View
                    </button>
                </td>
            </tr>
        `).join('');
    }
    
    async loadExportStats() {
        try {
            const data = await this.apiCall('/export/statistics');
            this.updateExportStats(data);
        } catch (error) {
            console.error('Failed to load export stats:', error);
        }
    }
    
    updateExportStats(stats) {
        if (Object.keys(stats).length === 0) {
            document.getElementById('export-stats').innerHTML = '<p>No export statistics available</p>';
            return;
        }
        
        document.getElementById('export-stats').innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <h4>Total Exports</h4>
                    <p>${stats.total_exports || 0}</p>
                </div>
                <div class="stat-item">
                    <h4>Total Records</h4>
                    <p>${stats.total_records_exported || 0}</p>
                </div>
                <div class="stat-item">
                    <h4>Total Size</h4>
                    <p>${stats.total_size_mb || 0} MB</p>
                </div>
                <div class="stat-item">
                    <h4>Latest Export</h4>
                    <p>${stats.latest_export ? new Date(stats.latest_export).toLocaleString() : 'None'}</p>
                </div>
            </div>
        `;
    }
    
    async loadConfiguration() {
        try {
            const data = await this.apiCall('/config');
            this.updateConfiguration(data);
        } catch (error) {
            this.showAlert('error', `Failed to load configuration: ${error.message}`);
        }
    }
    
    updateConfiguration(config) {
        document.getElementById('config-display').innerHTML = `
            <pre>${JSON.stringify(config, null, 2)}</pre>
        `;
    }
    
    async loadPerformanceStats() {
        try {
            const data = await this.apiCall('/performance/stats');
            this.updatePerformanceStats(data);
        } catch (error) {
            console.error('Failed to load performance stats:', error);
        }
    }
    
    updatePerformanceStats(stats) {
        const container = document.getElementById('performance-stats');
        if (!container) return;
        
        if (stats.message) {
            container.innerHTML = `<p>${stats.message}</p>`;
            return;
        }
        
        container.innerHTML = `
            <div class="performance-metrics">
                <h4>Performance Metrics</h4>
                <pre>${JSON.stringify(stats, null, 2)}</pre>
            </div>
        `;
    }
    
    async loadSystemHealth() {
        try {
            const data = await this.apiCall('/health');
            this.updateSystemHealth(data);
        } catch (error) {
            this.updateSystemHealth(null, error);
        }
    }
    
    updateSystemHealth(health, error = null) {
        const container = document.getElementById('system-health');
        if (!container) return;
        
        if (error) {
            container.innerHTML = '<div class="alert alert-error">System health check failed</div>';
            return;
        }
        
        const statusClass = health.status === 'healthy' ? 'alert-success' : 'alert-error';
        container.innerHTML = `
            <div class="alert ${statusClass}">
                <h4>System Health: ${health.status}</h4>
                <p><strong>Environment:</strong> ${health.environment}</p>
                <p><strong>Last Check:</strong> ${new Date(health.timestamp).toLocaleString()}</p>
            </div>
        `;
    }
    
    async startOrchestrator() {
        try {
            const data = await this.apiCall('/orchestrator/start', { method: 'POST' });
            this.showAlert('success', data.message);
            await this.loadSystemStatus();
        } catch (error) {
            this.showAlert('error', `Failed to start orchestrator: ${error.message}`);
        }
    }
    
    async stopOrchestrator() {
        try {
            const data = await this.apiCall('/orchestrator/stop', { method: 'POST' });
            this.showAlert('success', data.message);
            await this.loadSystemStatus();
        } catch (error) {
            this.showAlert('error', `Failed to stop orchestrator: ${error.message}`);
        }
    }
    
    async startCollectionJob() {
        const jobConfig = {
            trigger: 'manual',
            collection: { count: 20 },
            export_enabled: true
        };
        
        try {
            const data = await this.apiCall('/jobs/start', {
                method: 'POST',
                body: JSON.stringify(jobConfig)
            });
            this.showAlert('success', `Collection job started: ${data.job_id}`);
            await this.loadCurrentJob();
        } catch (error) {
            this.showAlert('error', `Failed to start collection job: ${error.message}`);
        }
    }
    
    async submitJobForm() {
        const form = document.getElementById('job-form');
        const formData = new FormData(form);
        
        const jobConfig = {
            trigger: 'manual',
            collection: {
                count: parseInt(formData.get('count')) || 20
            },
            export_enabled: formData.get('export_enabled') === 'on',
            quality_threshold: parseFloat(formData.get('quality_threshold')) || null
        };
        
        try {
            const data = await this.apiCall('/jobs/start', {
                method: 'POST',
                body: JSON.stringify(jobConfig)
            });
            this.showAlert('success', `Collection job started: ${data.job_id}`);
            await this.loadCurrentJob();
            form.reset();
        } catch (error) {
            this.showAlert('error', `Failed to start collection job: ${error.message}`);
        }
    }
    
    async submitExportForm() {
        const form = document.getElementById('export-form');
        const formData = new FormData(form);
        
        const exportConfig = {
            formats: Array.from(formData.getAll('formats')),
            compress: formData.get('compress') === 'on',
            include_metadata: formData.get('include_metadata') === 'on'
        };
        
        try {
            const data = await this.apiCall('/export', {
                method: 'POST',
                body: JSON.stringify(exportConfig)
            });
            this.showAlert('success', `Export completed: ${data.length} files created`);
            await this.loadExportStats();
            form.reset();
        } catch (error) {
            this.showAlert('error', `Export failed: ${error.message}`);
        }
    }
    
    async viewDramaDetail(dramaId) {
        try {
            const data = await this.apiCall(`/dramas/${dramaId}`);
            this.showDramaModal(data);
        } catch (error) {
            this.showAlert('error', `Failed to load drama details: ${error.message}`);
        }
    }
    
    showDramaModal(drama) {
        // Simple modal implementation
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${drama.title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <pre>${JSON.stringify(drama, null, 2)}</pre>
                </div>
            </div>
        `;
        
        modal.querySelector('.modal-close').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
        
        document.body.appendChild(modal);
    }
    
    showAlert(type, message) {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        alertContainer.appendChild(alert);
        
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }
    
    startAutoRefresh() {
        if (this.refreshInterval) return;
        
        this.refreshInterval = setInterval(() => {
            if (!this.isRefreshing) {
                this.refreshCurrentSection();
            }
        }, this.refreshRate);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    async refreshCurrentSection() {
        this.isRefreshing = true;
        try {
            await this.loadSectionData(this.currentSection);
        } catch (error) {
            console.error('Auto-refresh failed:', error);
        } finally {
            this.isRefreshing = false;
        }
    }
    
    async refreshAllData() {
        const button = document.getElementById('refresh-data');
        if (button) {
            button.disabled = true;
            button.textContent = 'Refreshing...';
        }
        
        try {
            await this.loadSectionData(this.currentSection);
            this.showAlert('success', 'Data refreshed successfully');
        } catch (error) {
            this.showAlert('error', `Refresh failed: ${error.message}`);
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = 'Refresh Data';
            }
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardApp();
});

// Modal styles (injected dynamically)
const modalStyles = `
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-content {
    background: white;
    border-radius: 10px;
    max-width: 80%;
    max-height: 80%;
    overflow: auto;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid #eee;
}

.modal-close {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #999;
}

.modal-close:hover {
    color: #333;
}

.modal-body {
    padding: 20px;
}
`;

// Inject modal styles
const styleSheet = document.createElement('style');
styleSheet.textContent = modalStyles;
document.head.appendChild(styleSheet);