// Configuration
const WS_URL = `ws://${window.location.hostname}:8001/ws/alerts`;

let alertsCount = 0;
let criticalCount = 0;
let attackData = {};

// Charts
let attackChart, trafficChart;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setupNavigation();
    connectWebSocket();
    refreshAll(); // Premier chargement
});

// Navigation logic
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('section');
    const sectionTitle = document.getElementById('section-title');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const target = item.getAttribute('data-section');
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            sections.forEach(s => s.classList.remove('active'));
            document.getElementById(target).classList.add('active');
            sectionTitle.innerText = item.innerText.trim();
        });
    });
}

// WebSocket Connection (Keep for real-time "blips")
function connectWebSocket() {
    const ws = new WebSocket(WS_URL);
    const statusBadge = document.getElementById('ws-status-badge');
    const statusText = document.getElementById('ws-status-text');

    ws.onopen = () => {
        statusBadge.className = 'status-badge connected';
        statusText.innerText = 'ONLINE';
    };

    ws.onclose = () => {
        statusBadge.className = 'status-badge disconnected';
        statusText.innerText = 'OFFLINE';
        setTimeout(connectWebSocket, 5000);
    };

    ws.onmessage = (event) => {
        const alert = JSON.parse(event.data);
        // On laisse le WebSocket ajouter le message immédiatement pour la réactivité
        addAlertToUI(alert, true); 
    };
}

// Global Refresh Loop (Every 2 seconds)
setInterval(refreshAll, 2000);

async function refreshAll() {
    await refreshStats();
    await loadRecentAlerts();
    if (document.getElementById('history').classList.contains('active')) {
        loadHistory();
    }
}

async function refreshStats() {
    try {
        const res = await fetch(`http://${window.location.hostname}:8001/api/stats`);
        const stats = await res.json();
        
        document.getElementById('total-alerts').innerText = stats.total_alerts;
        attackData = stats.attack_distribution;
        updateCharts();

        // Update Critical Count
        const critCount = stats.total_alerts - (stats.attack_distribution['BENIGN'] || 0);
        document.getElementById('critical-alerts').innerText = critCount;
    } catch (e) { console.log("SOC: Stats failed"); }
}

async function loadRecentAlerts() {
    try {
        const res = await fetch(`http://${window.location.hostname}:8001/api/alerts/recent?limit=15`);
        const alerts = await res.json();
        const list = document.getElementById('alerts-list');
        
        // On vide et on reconstruit pour garantir la cohérence
        const emptyState = list.querySelector('.empty-state');
        if (emptyState && alerts.length > 0) emptyState.remove();

        // Calcul de la confiance moyenne sur les 20 derniers
        if (alerts.length > 0) {
            const avg = alerts.reduce((acc, curr) => acc + parseFloat(curr.confidence), 0) / alerts.length;
            document.getElementById('avg-confidence').innerText = `${avg.toFixed(0)}%`;
        }

        // Mise à jour de la liste sans tout faire clignoter
        // Pour rester simple, on remplace le contenu si les IDs ont changé
        const currentIds = Array.from(list.querySelectorAll('.alert-item')).map(el => el.getAttribute('data-id'));
        const newIds = alerts.map(a => a.alert_id);

        if (JSON.stringify(currentIds) !== JSON.stringify(newIds)) {
            list.innerHTML = '';
            alerts.forEach(a => addAlertToUI(a, false));
        }
    } catch (e) { console.log("SOC: Alerts sync failed"); }
}

function addAlertToUI(alert, prepend) {
    const list = document.getElementById('alerts-list');
    
    // Éviter les doublons si le WebSocket et le Poll arrivent en même temps
    if (list.querySelector(`[data-id="${alert.alert_id}"]`)) return;

    const isCritical = alert.attack_type !== 'BENIGN';
    const alertEl = document.createElement('div');
    alertEl.className = `alert-item ${isCritical ? 'critical' : ''}`;
    alertEl.setAttribute('data-id', alert.alert_id);
    
    const time = new Date(alert.timestamp * 1000).toLocaleTimeString();
    const conf = parseFloat(alert.confidence).toFixed(1);

    alertEl.innerHTML = `
        <div class="alert-badge">${isCritical ? 'CRITICAL' : 'INFO'}</div>
        <div class="alert-info">
            <div class="alert-main">
                <span class="attack-name">${alert.attack_type}</span>
                <span class="attack-conf">${conf}% conf.</span>
            </div>
            <div class="attack-path">${alert.src_ip} <i class="fas fa-arrow-right"></i> ${alert.dst_ip}</div>
        </div>
        <div class="alert-time">${time}</div>
    `;

    if (prepend) list.insertBefore(alertEl, list.firstChild);
    else list.appendChild(alertEl);
}

// Charts
function initCharts() {
    const ctxAttack = document.getElementById('attackChart').getContext('2d');
    attackChart = new Chart(ctxAttack, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: ['#00d4ff', '#ff3e60', '#ffcc00', '#00ff94', '#7000ff'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 10, font: { size: 10 } } } }
        }
    });
}

function updateCharts() {
    attackChart.data.labels = Object.keys(attackData);
    attackChart.data.datasets[0].data = Object.values(attackData);
    attackChart.update();
}

async function loadHistory() {
    const body = document.getElementById('history-body');
    try {
        const res = await fetch(`http://${window.location.hostname}:8001/api/alerts/recent?limit=50`);
        const alerts = await res.json();
        body.innerHTML = '';
        alerts.forEach(a => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(a.timestamp * 1000).toLocaleString()}</td>
                <td style="color: ${a.attack_type !== 'BENIGN' ? 'var(--danger)' : 'inherit'}"><b>${a.attack_type}</b></td>
                <td>${a.src_ip}</td>
                <td>${a.dst_ip}</td>
                <td>${parseFloat(a.confidence).toFixed(1)}%</td>
            `;
            body.appendChild(row);
        });
    } catch (e) {}
}
