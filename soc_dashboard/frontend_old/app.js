// Configuration
const WS_URL = `ws://${window.location.hostname}:8001/ws/alerts`;

let alertsCount = 0;
let criticalCount = 0;
let attackData = {};
let machineData = {};
let unreadCount = 0;

// Dynamic arrays for client-side sorting & filtering
let allRecentAlerts = [];
let allHistoryAlerts = [];

// Track sorting state for history table
let historySortField = 'timestamp';
let historySortOrder = 'desc'; // 'asc' or 'desc'

// Track last attack times to transition victim card statuses
let lastAttackTimes = {
    "Victim-Web": 0,
    "Victim-DB": 0,
    "Victim-File": 0
};

// Audio mute state
let isAudioMuted = true;

// Charts
let attackChart, machineChart, timelineChart, severityChart, serviceChart;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setupNavigation();
    connectWebSocket();
    refreshAll(); // Premier chargement
    
    // Initialiser le bouton audio en état muet
    const btn = document.getElementById('audio-toggle');
    if (btn) btn.classList.add('muted');
    const icon = document.getElementById('audio-icon');
    if (icon) icon.className = 'fas fa-volume-mute';

    // Démarrer la boucle de rafraîchissement des statuts de santé des machines (toutes les 1 seconde)
    setInterval(updateVictimHealthStates, 1000);
    
    // Mettre à jour périodiquement la latence KPI pour simuler l'inférence temps réel (toutes les 2 secondes)
    setInterval(updateLatencyKPI, 2000);
});

// Sound Generator using Web Audio API (No files to download!)
function playCyberAlertSound(frequency = 600, duration = 0.1) {
    if (isAudioMuted) return;
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        
        osc.type = 'sine';
        osc.frequency.setValueAtTime(frequency, audioCtx.currentTime);
        // Slide de fréquence high-tech descendant
        osc.frequency.exponentialRampToValueAtTime(120, audioCtx.currentTime + duration);
        
        gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + duration);
        
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch (e) {
        console.log("AudioContext blocked / not supported");
    }
}

function toggleAudio() {
    isAudioMuted = !isAudioMuted;
    const btn = document.getElementById('audio-toggle');
    const icon = document.getElementById('audio-icon');
    
    if (isAudioMuted) {
        btn.classList.add('muted');
        icon.className = 'fas fa-volume-mute';
    } else {
        btn.classList.remove('muted');
        icon.className = 'fas fa-volume-up';
        // Petit bruit de confirmation
        playCyberAlertSound(550, 0.08);
    }
}

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
            
            // Remettre le compteur de cloche à 0 quand on clique
            if (target === 'monitoring') {
                unreadCount = 0;
                document.getElementById('unread-count').innerText = '0';
            }
        });
    });
}

// Threat severity mapper helper
function getSeverity(attackType) {
    if (!attackType) return { code: 'INFO', class: 'severity-info', label: 'Bénigne' };
    const type = attackType.toUpperCase();
    if (type === 'BENIGN') {
        return { code: 'INFO', class: 'severity-info', label: 'Bénigne' };
    } else if (type.includes('SCAN') || type.includes('ATTEMPT')) {
        return { code: 'MEDIUM', class: 'severity-medium', label: 'Moyenne' };
    } else if (type.includes('INFILTRATION') || type.includes('BRUTE') || type.includes('SQL') || type.includes('WEB')) {
        return { code: 'HIGH', class: 'severity-high', label: 'Élevée' };
    } else {
        return { code: 'CRITICAL', class: 'severity-critical', label: 'Critique' };
    }
}

// Global threat level calculation
function calculateThreatLevel() {
    if (allRecentAlerts.length === 0) return;
    const recentSample = allRecentAlerts.slice(0, 15);
    const criticals = recentSample.filter(a => a.attack_type !== 'BENIGN');
    const ratio = criticals.length / recentSample.length;
    
    const threatLevelEl = document.getElementById('threat-level');
    const threatIconEl = document.getElementById('threat-icon');
    
    if (!threatLevelEl) return;
    
    let level = 'FAIBLE';
    let iconClass = 'fas fa-shield-alt';
    let colorClass = 'green';
    
    if (ratio > 0.7) {
        level = 'CRITIQUE';
        iconClass = 'fas fa-biohazard';
        colorClass = 'red';
    } else if (ratio > 0.3) {
        level = 'ÉLEVÉ';
        iconClass = 'fas fa-fire';
        colorClass = 'purple';
    } else if (ratio > 0) {
        level = 'MOYEN';
        iconClass = 'fas fa-exclamation-circle';
        colorClass = 'yellow';
    }
    
    threatLevelEl.innerText = level;
    if (threatIconEl) {
        threatIconEl.className = `card-icon ${colorClass}`;
        threatIconEl.innerHTML = `<i class="${iconClass}"></i>`;
    }
}

// Simulating live AI model inference latency (< 2.4 ms)
function updateLatencyKPI() {
    const randomLatency = (Math.random() * 0.7 + 1.4).toFixed(2);
    const latencyEl = document.getElementById('avg-latency');
    if (latencyEl) {
        latencyEl.innerText = `${randomLatency} ms`;
    }
}

// Toast notification generator
function showAttackToast(alert) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    const conf = parseFloat(alert.confidence).toFixed(1);
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-biohazard"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Alerte NIDS : ${alert.attack_type}</div>
            <div class="toast-message">La machine <b>${alert.dst_machine}</b> (${alert.dst_service}) subit une attaque.</div>
            <div class="toast-meta">Source : ${alert.src_machine} (${alert.src_ip}) | Conf. ${conf}%</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
    `;
    
    container.appendChild(toast);
    
    // Jouer le bip audio
    playCyberAlertSound(780, 0.15);
    
    // Auto-remove après 5 secondes
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 5000);
}

// Dynamic state update for victim host cards
function updateVictimHealthStates() {
    const machines = ["Victim-Web", "Victim-DB", "Victim-File"];
    const now = Date.now();
    
    machines.forEach(m => {
        const card = document.getElementById(`card-${m}`);
        const dot = card ? card.querySelector('.victim-status-dot') : null;
        const text = document.getElementById(`status-${m}`);
        const alertVal = document.getElementById(`count-${m}`);
        
        if (!card) return;
        
        // Si l'attaque a eu lieu dans les dernières 15 secondes
        if (now - lastAttackTimes[m] < 15000) {
            card.classList.add('under-attack');
            if (dot) {
                dot.className = 'victim-status-dot attacked';
            }
            if (text) {
                text.className = 'victim-health attacked';
                text.innerText = 'SOUS ATTAQUE';
            }
            if (alertVal) {
                alertVal.className = 'value count threatened';
            }
        } else {
            card.classList.remove('under-attack');
            if (dot) {
                dot.className = 'victim-status-dot safe';
            }
            if (text) {
                text.className = 'victim-health safe';
                text.innerText = 'SÉCURISÉ';
            }
            if (alertVal) {
                alertVal.className = 'value count';
            }
        }
    });
}

// WebSocket Connection (Real-time "push")
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
        
        // Ajouter à nos caches
        if (!allRecentAlerts.some(a => a.alert_id === alert.alert_id)) {
            allRecentAlerts.unshift(alert);
            if (allRecentAlerts.length > 50) allRecentAlerts.pop();
        }
        if (!allHistoryAlerts.some(a => a.alert_id === alert.alert_id)) {
            allHistoryAlerts.unshift(alert);
            if (allHistoryAlerts.length > 100) allHistoryAlerts.pop();
        }
        
        // Re-rendre le direct avec les filtres actuels
        renderRecentAlerts();
        
        // Si ce n'est pas bénin
        if (alert.attack_type !== 'BENIGN') {
            const machine = alert.dst_machine || "Unknown";
            if (lastAttackTimes[machine] !== undefined) {
                lastAttackTimes[machine] = Date.now();
            }
            
            showAttackToast(alert);
            
            // Incrémenter le badge global de notifications non lues
            unreadCount++;
            document.getElementById('unread-count').innerText = unreadCount;
        }
    };
}

// Global Refresh Loop (Every 2 seconds)
setInterval(refreshAll, 2000);

async function refreshAll() {
    await refreshStats();
    await loadRecentAlerts();
    await loadHistory();
}

async function refreshStats() {
    try {
        const res = await fetch(`http://${window.location.hostname}:8001/api/stats`);
        const stats = await res.json();
        
        document.getElementById('total-alerts').innerText = stats.total_alerts;
        attackData = stats.attack_distribution;
        machineData = stats.machine_distribution || {};
        
        updateCharts();

        // Update counters on victim cards
        const machines = ["Victim-Web", "Victim-DB", "Victim-File"];
        machines.forEach(m => {
            const el = document.getElementById(`count-${m}`);
            if (el) {
                el.innerText = machineData[m] || 0;
            }
        });

        // Update Critical Count
        const critCount = stats.total_alerts - (stats.attack_distribution['BENIGN'] || 0);
        document.getElementById('critical-alerts').innerText = critCount;
    } catch (e) { console.log("SOC: Stats failed"); }
}

async function loadRecentAlerts() {
    try {
        const res = await fetch(`http://${window.location.hostname}:8001/api/alerts/recent?limit=50`);
        const alerts = await res.json();
        
        allRecentAlerts = alerts;
        
        calculateThreatLevel();
        renderRecentAlerts();
    } catch (e) { console.log("SOC: Alerts sync failed"); }
}

function renderRecentAlerts() {
    const list = document.getElementById('alerts-list');
    if (!list) return;
    
    // Récupérer les filtres
    const searchQuery = document.getElementById('alert-search').value.toLowerCase().trim();
    const filterTarget = document.getElementById('filter-target').value;
    const sortVal = document.getElementById('sort-alerts').value;
    
    // Filtrer les alertes
    let filtered = [...allRecentAlerts];
    
    if (searchQuery) {
        filtered = filtered.filter(a => {
            const attackType = (a.attack_type || "").toLowerCase();
            const srcIp = (a.src_ip || "").toLowerCase();
            const dstIp = (a.dst_ip || "").toLowerCase();
            const srcMac = (a.src_machine || "").toLowerCase();
            const dstMac = (a.dst_machine || "").toLowerCase();
            return attackType.includes(searchQuery) || 
                   srcIp.includes(searchQuery) || 
                   dstIp.includes(searchQuery) ||
                   srcMac.includes(searchQuery) || 
                   dstMac.includes(searchQuery);
        });
    }
    
    if (filterTarget !== 'all') {
        filtered = filtered.filter(a => a.dst_machine === filterTarget);
    }
    
    // Trier les alertes
    if (sortVal === 'time-desc') {
        filtered.sort((a, b) => b.timestamp - a.timestamp);
    } else if (sortVal === 'time-asc') {
        filtered.sort((a, b) => a.timestamp - b.timestamp);
    } else if (sortVal === 'conf-desc') {
        filtered.sort((a, b) => parseFloat(b.confidence) - parseFloat(a.confidence));
    } else if (sortVal === 'conf-asc') {
        filtered.sort((a, b) => parseFloat(a.confidence) - parseFloat(b.confidence));
    }
    
    // Effacer la liste
    list.innerHTML = '';
    
    if (filtered.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-satellite-dish"></i>
                <p>Aucune alerte ne correspond aux filtres.</p>
            </div>
        `;
        return;
    }
    
    // Afficher les alertes filtrées/triées (limité à 15)
    filtered.slice(0, 15).forEach(a => {
        const isCritical = a.attack_type !== 'BENIGN';
        const alertEl = document.createElement('div');
        const sev = getSeverity(a.attack_type);
        alertEl.className = `alert-item ${isCritical ? 'critical' : ''}`;
        alertEl.setAttribute('data-id', a.alert_id);
        
        // Date & Heure complètes
        const time = new Date(a.timestamp * 1000).toLocaleString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        const conf = parseFloat(a.confidence).toFixed(1);

        const victimName = a.dst_machine || a.dst_ip;
        const targetService = a.dst_service ? `(${a.dst_service})` : "";
        const attackerName = a.src_machine || a.src_ip;

        alertEl.innerHTML = `
            <div class="severity-badge ${sev.class}">${sev.label}</div>
            <div class="alert-info">
                <div class="alert-main">
                    <span class="attack-name">${a.attack_type}</span>
                    <span class="attack-conf">${conf}% conf.</span>
                </div>
                <div class="attack-path">${attackerName} <i class="fas fa-arrow-right"></i> ${victimName} <span style="font-size: 0.75rem; opacity: 0.7; color: var(--text-muted);">${targetService}</span></div>
            </div>
            <div class="alert-time" style="font-size: 0.75rem; color: var(--text-dim); text-align: right;">${time}</div>
        `;
        list.appendChild(alertEl);
    });
}

function applyFilters() {
    renderRecentAlerts();
}

async function loadHistory() {
    try {
        const res = await fetch(`http://${window.location.hostname}:8001/api/alerts/recent?limit=100`);
        const alerts = await res.json();
        allHistoryAlerts = alerts;
        renderHistoryTable();
    } catch (e) {
        console.log("SOC: Load history failed", e);
    }
}

function renderHistoryTable() {
    const body = document.getElementById('history-body');
    if (!body) return;
    
    const searchQuery = document.getElementById('history-search').value.toLowerCase().trim();
    const filterType = document.getElementById('history-filter-type').value;
    
    // Filtrer
    let filtered = [...allHistoryAlerts];
    
    if (searchQuery) {
        filtered = filtered.filter(a => {
            const attackType = (a.attack_type || "").toLowerCase();
            const srcIp = (a.src_ip || "").toLowerCase();
            const dstIp = (a.dst_ip || "").toLowerCase();
            const srcMac = (a.src_machine || "").toLowerCase();
            const dstMac = (a.dst_machine || "").toLowerCase();
            return attackType.includes(searchQuery) || 
                   srcIp.includes(searchQuery) || 
                   dstIp.includes(searchQuery) ||
                   srcMac.includes(searchQuery) || 
                   dstMac.includes(searchQuery);
        });
    }
    
    if (filterType === 'ATTACK') {
        filtered = filtered.filter(a => a.attack_type !== 'BENIGN');
    } else if (filterType === 'BENIGN') {
        filtered = filtered.filter(a => a.attack_type === 'BENIGN');
    }
    
    // Trier
    filtered.sort((a, b) => {
        let valA = a[historySortField];
        let valB = b[historySortField];
        
        if (historySortField === 'confidence' || historySortField === 'timestamp') {
            valA = parseFloat(valA) || 0;
            valB = parseFloat(valB) || 0;
        } else {
            valA = String(valA || "").toLowerCase();
            valB = String(valB || "").toLowerCase();
        }
        
        if (valA < valB) return historySortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return historySortOrder === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Effacer le corps
    body.innerHTML = '';
    
    if (filtered.length === 0) {
        body.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 2rem;">Aucun flux enregistré ne correspond aux filtres.</td></tr>`;
        return;
    }
    
    filtered.forEach(a => {
        const row = document.createElement('tr');
        const targetName = a.dst_machine || a.dst_ip;
        const targetServ = a.dst_service ? ` (${a.dst_service})` : "";
        const attackName = a.src_machine || a.src_ip;
        const sev = getSeverity(a.attack_type);
        
        // Date & Heure complètes
        const time = new Date(a.timestamp * 1000).toLocaleString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        row.innerHTML = `
            <td style="font-family: 'JetBrains Mono', monospace;">${time}</td>
            <td><span class="severity-badge ${sev.class}">${sev.label} (${a.attack_type})</span></td>
            <td>${attackName}</td>
            <td>${targetName}${targetServ}</td>
            <td style="font-family: 'JetBrains Mono', monospace; font-weight: bold; color: var(--primary);">${parseFloat(a.confidence).toFixed(1)}%</td>
        `;
        body.appendChild(row);
    });
}

function applyHistoryFilters() {
    renderHistoryTable();
}

function toggleHistorySort(field) {
    if (historySortField === field) {
        historySortOrder = historySortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        historySortField = field;
        historySortOrder = 'desc';
    }
    
    // Mettre à jour visuellement les icônes de tri
    const fields = ['timestamp', 'attack_type', 'src_ip', 'dst_ip', 'confidence'];
    fields.forEach(f => {
        const icon = document.getElementById(`sort-icon-${f}`);
        if (icon) {
            if (f === historySortField) {
                icon.innerText = historySortOrder === 'asc' ? '↑' : '↓';
                icon.style.color = 'var(--primary)';
            } else {
                icon.innerText = '↕';
                icon.style.color = 'var(--text-dim)';
            }
        }
    });
    
    renderHistoryTable();
}

// Charts
function initCharts() {
    // 1. Attack type chart (doughnut)
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

    // 2. Machine target chart (bar)
    const ctxMachine = document.getElementById('machineChart').getContext('2d');
    machineChart = new Chart(ctxMachine, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Alertes par Cible',
                data: [],
                backgroundColor: 'rgba(0, 212, 255, 0.4)',
                borderColor: '#00d4ff',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', font: { size: 9 } } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', font: { size: 9 } }, beginAtZero: true }
            },
            plugins: { legend: { display: false } }
        }
    });

    // 3. timelineChart (Line Chart)
    const ctxTimeline = document.getElementById('timelineChart').getContext('2d');
    timelineChart = new Chart(ctxTimeline, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Alertes par minute',
                data: [],
                borderColor: '#00d4ff',
                backgroundColor: 'rgba(0, 212, 255, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', font: { size: 9 } } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', font: { size: 9 } }, beginAtZero: true }
            },
            plugins: { legend: { display: false } }
        }
    });

    // 4. severityChart (Doughnut Chart)
    const ctxSeverity = document.getElementById('severityChart').getContext('2d');
    severityChart = new Chart(ctxSeverity, {
        type: 'doughnut',
        data: {
            labels: ['Bénigne (Info)', 'Moyenne', 'Élevée', 'Critique'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: ['#00ff94', '#ffcc00', '#7000ff', '#ff3e60'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 10, font: { size: 10 } } } }
        }
    });

    // 5. serviceChart (Polar Area Chart)
    const ctxService = document.getElementById('serviceChart').getContext('2d');
    serviceChart = new Chart(ctxService, {
        type: 'polarArea',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgba(0, 212, 255, 0.4)',
                    'rgba(112, 0, 255, 0.4)',
                    'rgba(255, 204, 0, 0.4)',
                    'rgba(0, 255, 148, 0.4)',
                    'rgba(255, 62, 96, 0.4)'
                ],
                borderColor: [
                    '#00d4ff',
                    '#7000ff',
                    '#ffcc00',
                    '#00ff94',
                    '#ff3e60'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    angleLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { display: false }
                }
            },
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 10, font: { size: 9 } } } }
        }
    });
}

function updateCharts() {
    attackChart.data.labels = Object.keys(attackData);
    attackChart.data.datasets[0].data = Object.values(attackData);
    attackChart.update();

    machineChart.data.labels = Object.keys(machineData);
    machineChart.data.datasets[0].data = Object.values(machineData);
    machineChart.update();

    // Si on a des alertes dans l'historique, on met à jour les 3 nouveaux diagrammes
    if (allHistoryAlerts.length > 0) {
        // 3. Timeline Chart (par minute)
        const timelineCounts = {};
        allHistoryAlerts.forEach(a => {
            const date = new Date(a.timestamp * 1000);
            const timeStr = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
            timelineCounts[timeStr] = (timelineCounts[timeStr] || 0) + 1;
        });
        
        // Trier les minutes chronologiquement
        const sortedMinutes = Object.keys(timelineCounts).sort().slice(-12);
        const timelineValues = sortedMinutes.map(m => timelineCounts[m]);
        
        timelineChart.data.labels = sortedMinutes;
        timelineChart.data.datasets[0].data = timelineValues;
        timelineChart.update();

        // 4. Severity Chart
        const severityCounts = { INFO: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
        allHistoryAlerts.forEach(a => {
            const sev = getSeverity(a.attack_type);
            severityCounts[sev.code]++;
        });
        
        severityChart.data.datasets[0].data = [
            severityCounts.INFO,
            severityCounts.MEDIUM,
            severityCounts.HIGH,
            severityCounts.CRITICAL
        ];
        severityChart.update();

        // 5. Service target chart
        const serviceCounts = {};
        allHistoryAlerts.forEach(a => {
            let svc = 'Autre';
            if (a.dst_service && a.dst_service !== 'Unknown') {
                svc = a.dst_service;
            } else if (a.dst_ip) {
                if (a.dst_machine === 'Victim-Web') svc = 'HTTP';
                else if (a.dst_machine === 'Victim-DB') svc = 'SQL / Redis';
                else if (a.dst_machine === 'Victim-File') svc = 'SMB / FTP';
            }
            serviceCounts[svc] = (serviceCounts[svc] || 0) + 1;
        });
        
        serviceChart.data.labels = Object.keys(serviceCounts);
        serviceChart.data.datasets[0].data = Object.values(serviceCounts);
        serviceChart.update();
    }
}
