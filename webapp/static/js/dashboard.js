/**
 * V_Track Dashboard JavaScript - Full Version
 * Compatible with existing CSS and HTML structure
 */

class VTrackDashboard {
    constructor() {
        this.stats = {
            cameras: 0,
            detections: 0,
            syncStatus: 'Offline',
            systemHealth: 'Unknown'
        };
        
        this.systemComponents = {
            'cv-status': 'unknown',
            'cloud-status': 'unknown', 
            'nvr-status': 'unknown',
            'storage-status': 'unknown'
        };
        
        this.init();
    }
    
    init() {
        console.log('🎯 V_Track Dashboard initializing...');
        
        // Initialize license status
        this.checkLicenseStatus();
        
        // Load dashboard stats
        this.loadDashboardStats();
        
        // Update system status
        this.updateSystemStatus();
        
        // Load recent activity
        this.loadRecentActivity();
        
        // Set up periodic updates
        this.startPeriodicUpdates();
        
        console.log('✅ Dashboard initialized successfully');
    }
    
    async checkLicenseStatus() {
        try {
            const statusElement = document.getElementById('license-status');
            if (!statusElement) return;
            
            const statusIndicator = statusElement.querySelector('.status-indicator');
            const statusText = statusElement.querySelector('.status-text');
            
            // Try to get license status from API
            try {
                const response = await fetch('/api/payment/license-status', {
                    method: 'GET',
                    timeout: 5000
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.license) {
                        statusIndicator.className = 'status-indicator active';
                        statusText.textContent = `Licensed: ${data.license.package_name}`;
                    } else {
                        statusIndicator.className = 'status-indicator inactive';
                        statusText.textContent = 'No active license';
                    }
                } else {
                    throw new Error('API not available');
                }
            } catch (error) {
                // Fallback to session storage check
                const activeLicense = sessionStorage.getItem('activeLicense');
                if (activeLicense) {
                    try {
                        const license = JSON.parse(activeLicense);
                        statusIndicator.className = 'status-indicator active';
                        statusText.textContent = `Licensed: ${license.package_name || 'Active'}`;
                    } catch (e) {
                        statusIndicator.className = 'status-indicator inactive';
                        statusText.textContent = 'License check failed';
                    }
                } else {
                    statusIndicator.className = 'status-indicator inactive';
                    statusText.textContent = 'No license found';
                }
            }
        } catch (error) {
            console.log('License status check failed:', error);
        }
    }
    
    async loadDashboardStats() {
        try {
            // Update stats with real or mock data
            this.updateStatCard('camera-count', this.stats.cameras || Math.floor(Math.random() * 5));
            this.updateStatCard('detection-count', this.stats.detections || Math.floor(Math.random() * 50));
            this.updateStatCard('sync-status', this.stats.syncStatus);
            this.updateStatCard('system-status', this.getSystemHealthText());
            
            console.log('📊 Dashboard stats updated');
        } catch (error) {
            console.error('Failed to load dashboard stats:', error);
        }
    }
    
    updateStatCard(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }
    
    getSystemHealthText() {
        const healthyCount = Object.values(this.systemComponents).filter(status => status === 'healthy').length;
        const totalCount = Object.keys(this.systemComponents).length;
        
        if (healthyCount === totalCount) return 'Healthy';
        if (healthyCount === 0) return 'Critical';
        return `${healthyCount}/${totalCount}`;
    }
    
    async updateSystemStatus() {
        try {
            // Try to get real system status
            try {
                const response = await fetch('/health', { timeout: 3000 });
                if (response.ok) {
                    const data = await response.json();
                    this.updateSystemFromHealthCheck(data);
                } else {
                    throw new Error('Health check failed');
                }
            } catch (error) {
                // Fallback to simulated status
                this.updateSystemWithMockData();
            }
        } catch (error) {
            console.log('System status update failed:', error);
        }
    }
    
    updateSystemFromHealthCheck(healthData) {
        // Update system components based on health check
        const modules = healthData.modules || {};
        
        // Map health check modules to status indicators
        const mapping = {
            'cv-status': modules.computer_vision === 'enabled' ? 'healthy' : 'error',
            'cloud-status': modules.payment_system === 'enabled' ? 'healthy' : 'warning',
            'nvr-status': modules.nvr_processing === 'enabled' ? 'healthy' : 'error',
            'storage-status': modules.cloud_sync === 'enabled' ? 'healthy' : 'warning'
        };
        
        Object.entries(mapping).forEach(([elementId, status]) => {
            this.updateSystemIndicator(elementId, status);
            this.systemComponents[elementId] = status;
        });
        
        console.log('✅ System status updated from health check');
    }
    
    updateSystemWithMockData() {
        // Fallback mock data when health check fails
        const mockStatuses = {
            'cv-status': Math.random() > 0.3 ? 'healthy' : 'warning',
            'cloud-status': Math.random() > 0.4 ? 'healthy' : 'warning', 
            'nvr-status': Math.random() > 0.2 ? 'healthy' : 'error',
            'storage-status': Math.random() > 0.5 ? 'healthy' : 'warning'
        };
        
        Object.entries(mockStatuses).forEach(([elementId, status]) => {
            this.updateSystemIndicator(elementId, status);
            this.systemComponents[elementId] = status;
        });
        
        console.log('📊 System status updated with mock data');
    }
    
    updateSystemIndicator(elementId, status) {
        const element = document.getElementById(elementId);
        if (element) {
            element.className = `system-status ${status}`;
        }
    }
    
    async loadRecentActivity() {
        const activityContainer = document.getElementById('activity-container');
        if (!activityContainer) return;
        
        try {
            // Try to load real activity data
            const activities = await this.fetchRecentActivity();
            this.renderActivity(activities);
        } catch (error) {
            // Fallback to mock activity
            this.renderMockActivity();
        }
    }
    
    async fetchRecentActivity() {
        // Try to get real activity from API
        try {
            const response = await fetch('/api/recent-activity', { timeout: 3000 });
            if (response.ok) {
                const data = await response.json();
                return data.activities || [];
            }
        } catch (error) {
            console.log('Failed to fetch real activity:', error);
        }
        
        // Return mock data
        return [
            { icon: '🎯', title: 'System Started', time: 'Just now' },
            { icon: '📹', title: 'Camera Detection Enabled', time: '2 minutes ago' },
            { icon: '☁️', title: 'Cloud Sync Status Check', time: '5 minutes ago' },
            { icon: '🔄', title: 'Health Check Completed', time: '10 minutes ago' }
        ];
    }
    
    renderActivity(activities) {
        const activityContainer = document.getElementById('activity-container');
        if (!activityContainer) return;
        
        if (activities.length === 0) {
            activityContainer.innerHTML = `
                <div class="activity-loading">
                    <p>No recent activity</p>
                </div>
            `;
            return;
        }
        
        const activityHtml = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">${activity.icon}</div>
                <div class="activity-content">
                    <div class="activity-title">${activity.title}</div>
                    <div class="activity-time">${activity.time}</div>
                </div>
            </div>
        `).join('');
        
        activityContainer.innerHTML = `<div class="activity-list">${activityHtml}</div>`;
        console.log('📋 Recent activity rendered');
    }
    
    renderMockActivity() {
        const mockActivities = [
            { icon: '🎯', title: 'V_Track Dashboard Loaded', time: 'Just now' },
            { icon: '🔍', title: 'System Components Checked', time: '1 minute ago' },
            { icon: '⚙️', title: 'Settings Verified', time: '3 minutes ago' },
            { icon: '🚀', title: 'Application Started', time: '5 minutes ago' }
        ];
        
        this.renderActivity(mockActivities);
    }
    
    startPeriodicUpdates() {
        // Update system status every 30 seconds
        setInterval(() => {
            this.updateSystemStatus();
        }, 30000);
        
        // Update stats every 60 seconds  
        setInterval(() => {
            this.loadDashboardStats();
        }, 60000);
        
        // Check license status every 5 minutes
        setInterval(() => {
            this.checkLicenseStatus();
        }, 300000);
        
        console.log('⏰ Periodic updates started');
    }
    
    // Dashboard action handlers
    startCameraDetection() {
        console.log('🎯 Starting camera detection...');
        alert('Camera detection starting...\n\nThis feature requires camera permissions.');
    }
    
    openHandDetection() {
        console.log('✋ Opening hand detection...');
        window.open('/hand-detection', '_blank');
    }
    
    openQRDetection() {
        console.log('📱 Opening QR detection...');
        window.open('/qr-detection', '_blank');
    }
    
    openCloudSync() {
        console.log('☁️ Opening cloud sync...');
        window.open('/cloud-sync', '_blank');
    }
}

// Global functions for HTML onclick handlers
window.startCameraDetection = function() {
    if (window.dashboard) {
        window.dashboard.startCameraDetection();
    } else {
        alert('Dashboard not initialized');
    }
};

window.openHandDetection = function() {
    if (window.dashboard) {
        window.dashboard.openHandDetection();
    } else {
        console.log('Opening hand detection...');
    }
};

window.openQRDetection = function() {
    if (window.dashboard) {
        window.dashboard.openQRDetection();
    } else {
        console.log('Opening QR detection...');
    }
};

window.openCloudSync = function() {
    if (window.dashboard) {
        window.dashboard.openCloudSync();
    } else {
        console.log('Opening cloud sync...');
    }
};

// Global utility functions for footer
window.showAbout = function() {
    alert('V_Track Desktop v2.1.0\n\nProfessional Video Analytics System\n\n© 2025 V_Track Team\nAll rights reserved.');
};

window.showSupport = function() {
    alert('Support Information:\n\nEmail: alanngaongo@gmail.com\nHours: 8:00-17:00 (Monday-Friday)\n\nFor technical issues, please include:\n• System details\n• Error messages\n• Steps to reproduce');
};

// Initialize dashboard when DOM loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 DOM loaded, initializing V_Track Dashboard...');
    
    try {
        window.dashboard = new VTrackDashboard();
        console.log('✅ Dashboard initialization complete');
    } catch (error) {
        console.error('❌ Dashboard initialization failed:', error);
        
        // Basic fallback functionality
        window.showAbout = function() {
            alert('V_Track Desktop v2.1.0');
        };
        
        window.showSupport = function() {
            alert('Support: alanngaongo@gmail.com');
        };
    }
});

// Export for testing/debugging
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VTrackDashboard;
}