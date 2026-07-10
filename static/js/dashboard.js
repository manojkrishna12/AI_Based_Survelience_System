// dashboard.js - Handles statistics visualization and live polling updates

document.addEventListener('DOMContentLoaded', function() {
    // Check if chart elements exist before executing chart rendering
    const typeChartCanvas = document.getElementById('alertTypeChart');
    const hourlyChartCanvas = document.getElementById('hourlyDistributionChart');
    
    if (typeChartCanvas && hourlyChartCanvas) {
        initializeCharts();
    }
    
    // Check if recent alerts list exists
    const recentAlertList = document.getElementById('recent-alerts-list');
    if (recentAlertList) {
        // Start polling for new alerts every 4 seconds
        setInterval(pollRecentAlerts, 4000);
    }
});

let typeChart = null;
let hourlyChart = null;

/**
 * Initialize charts with data loaded via API
 */
function initializeCharts() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            renderAlertTypeChart(data.alerts_by_type || {});
            renderHourlyChart(data.hourly_distribution || {});
        })
        .catch(err => console.error('Error fetching stats:', err));
}

/**
 * Render Doughnut chart showing Alert types count
 */
function renderAlertTypeChart(typeData) {
    const ctx = document.getElementById('alertTypeChart').getContext('2d');
    
    const labels = ['Human', 'Face', 'Motion', 'Intrusion', 'Fire/Smoke', 'Manual'];
    const counts = labels.map(label => typeData[label] || 0);
    
    const colors = [
        '#3b82f6', // blue (human)
        '#8b5cf6', // purple (face)
        '#f59e0b', // yellow (motion)
        '#ef4444', // red (intrusion)
        '#f97316', // orange (fire)
        '#64748b'  // slate (manual)
    ];
    
    typeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { family: 'Inter', size: 11 },
                        padding: 15
                    }
                }
            },
            cutout: '65%'
        }
    });
}

/**
 * Render Line chart showing alert distribution hourly
 */
function renderHourlyChart(hourlyData) {
    const ctx = document.getElementById('hourlyDistributionChart').getContext('2d');
    
    // Generate label hours: 00 to 23
    const labels = [];
    const counts = [];
    
    for (let i = 0; i < 24; i++) {
        const hourStr = i.toString().padStart(2, '0');
        labels.push(hourStr + ':00');
        counts.push(hourlyData[hourStr] || 0);
    }
    
    hourlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Alert Frequency (Last 24 Hours)',
                data: counts,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: '#1e3a8a',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: { family: 'Inter' }
                    },
                    grid: { color: '#f1f5f9' }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        maxTicksLimit: 8,
                        font: { family: 'Inter' }
                    }
                }
            }
        }
    });
}

// Track IDs of currently displayed alerts to prevent duplicates and detect new alerts
let displayedAlertIds = new Set();

/**
 * Poll recent alerts endpoint to show real-time additions
 */
function pollRecentAlerts() {
    // On first load, harvest IDs already in DOM
    const alertItems = document.querySelectorAll('.recent-alert-item');
    if (displayedAlertIds.size === 0 && alertItems.length > 0) {
        alertItems.forEach(item => {
            const alertId = parseInt(item.dataset.alertId);
            if (alertId) displayedAlertIds.add(alertId);
        });
    }

    fetch('/api/recent_alerts?limit=8')
        .then(response => response.json())
        .then(alerts => {
            const listContainer = document.getElementById('recent-alerts-list');
            if (!listContainer) return;
            
            let hasNew = false;
            
            // Loop in reverse order to prepend oldest new alerts first
            alerts.reverse().forEach(alert => {
                if (!displayedAlertIds.has(alert.id)) {
                    hasNew = true;
                    displayedAlertIds.add(alert.id);
                    
                    // Create element and prepend
                    const alertHtml = createAlertHtmlElement(alert);
                    listContainer.insertAdjacentHTML('afterbegin', alertHtml);
                    
                    // Trigger sound/alert notification in browser if needed
                    playAlertSound(alert.alert_type);
                }
            });
            
            // Limit shown alerts list length to 10
            const currentItems = listContainer.querySelectorAll('.recent-alert-item');
            if (currentItems.length > 10) {
                for (let i = 10; i < currentItems.length; i++) {
                    currentItems[i].remove();
                }
            }
            
            // If new alerts were added, update charts and counters
            if (hasNew) {
                updateMetricsAndCharts();
            }
        })
        .catch(err => console.error('Error polling alerts:', err));
}

/**
 * Generate HTML string for an alert row item
 */
function createAlertHtmlElement(alert) {
    const formattedDate = formatTime(alert.created_at);
    const badgeClass = `badge-${alert.alert_type.toLowerCase().replace('/', '-')}`;
    const imgUrl = alert.image_path || '/static/images/placeholder.jpg';
    
    return `
        <div class="recent-alert-item animate__animated animate__fadeInDown" data-alert-id="${alert.id}">
            <img class="alert-thumbnail" src="${imgUrl}" alt="Capture" onerror="this.src='https://placehold.co/60x60/0f172a/ffffff?text=Capture'">
            <div class="alert-info-mini">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <h6 class="mb-0 text-dark">${alert.camera_name || 'System Feed'}</h6>
                    <span class="badge alert-badge ${badgeClass}">${alert.alert_type}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <p class="mb-0 text-muted">Confidence: ${(alert.confidence * 100).toFixed(0)}%</p>
                    <span class="alert-time text-muted font-monospace">${formattedDate}</span>
                </div>
            </div>
        </div>
    `;
}

/**
 * Fetch fresh stats JSON and redraw graphs
 */
function updateMetricsAndCharts() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update counts in UI widgets
            const alertsTodayEl = document.getElementById('widget-alerts-today');
            if (alertsTodayEl) alertsTodayEl.textContent = data.total_alerts;
            
            // Redraw charts
            if (typeChart) {
                const labels = ['Human', 'Face', 'Motion', 'Intrusion', 'Fire/Smoke', 'Manual'];
                const counts = labels.map(label => data.alerts_by_type[label] || 0);
                typeChart.data.datasets[0].data = counts;
                typeChart.update();
            }
            
            if (hourlyChart) {
                const counts = [];
                for (let i = 0; i < 24; i++) {
                    const hourStr = i.toString().padStart(2, '0');
                    counts.push(data.hourly_distribution[hourStr] || 0);
                }
                hourlyChart.data.datasets[0].data = counts;
                hourlyChart.update();
            }
        })
        .catch(err => console.error('Error updating charts:', err));
}

/**
 * Parse date strings from SQLite
 */
function formatTime(sqliteDateStr) {
    if (!sqliteDateStr) return '';
    try {
        const parts = sqliteDateStr.split(' ');
        if (parts.length > 1) {
            // Return only HH:MM:SS
            return parts[1].split('.')[0];
        }
        return sqliteDateStr;
    } catch(e) {
        return sqliteDateStr;
    }
}

/**
 * Play a web notification beep for critical alert events (Intrusion/Fire)
 */
function playAlertSound(type) {
    if (type === 'Intrusion' || type === 'Fire/Smoke') {
        try {
            const context = new (window.AudioContext || window.webkitAudioContext)();
            const osc = context.createOscillator();
            const gain = context.createGain();
            
            osc.type = 'sine';
            osc.frequency.setValueAtTime(type === 'Fire/Smoke' ? 880 : 660, context.currentTime); // Sound pitch
            gain.gain.setValueAtTime(0.1, context.currentTime);
            
            osc.connect(gain);
            gain.connect(context.destination);
            
            osc.start();
            osc.stop(context.currentTime + 0.3); // duration
        } catch(e) {
            console.log('AudioContext blocked by browser interaction policy.');
        }
    }
}
