import React, { useState, useEffect, useRef, useMemo } from 'react';
import Sidebar from './Components/Sidebar';
import StatsPanel from './Components/StatsPanel';
import VictimsGrid from './Components/VictimsGrid';
import LiveFeed from './Components/LiveFeed';
import HistoryTable from './Components/HistoryTable';
import AnalyticsTab from './Components/AnalyticsTab';
import SettingsTab from './Components/SettingsTab';
import { Volume2, VolumeX, ShieldAlert, Wifi, Bell, Shield, Sun, Moon } from 'lucide-react';
import Chart from 'chart.js/auto';

const API_HOSTNAME = window.location.hostname || 'localhost';
const WS_URL = `ws://${API_HOSTNAME}:8001/ws/alerts`;
const API_URL = `http://${API_HOSTNAME}:8001/api`;

export default function App() {
  const [activeSection, setActiveSection] = useState('monitoring');
  
  // Dashboard stats & KPIs
  const [totalAlerts, setTotalAlerts] = useState(0);
  const [criticalAlerts, setCriticalAlerts] = useState(0);
  const [avgLatency, setAvgLatency] = useState('1.80');
  const [threatLevel, setThreatLevel] = useState('FAIBLE');
  const [wsConnected, setWsConnected] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  
  // Audio state
  const [isAudioMuted, setIsAudioMuted] = useState(true);

  // Active alerts arrays
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [historyAlerts, setHistoryAlerts] = useState([]);

  // Toast notifications array
  const [toasts, setToasts] = useState([]);

  // Live monitor states
  const [liveSearch, setLiveSearch] = useState('');
  const [liveTarget, setLiveTarget] = useState('all');
  const [liveSort, setLiveSort] = useState('time-desc');
  const [liveStartDate, setLiveStartDate] = useState('');
  const [liveEndDate, setLiveEndDate] = useState('');

  // History states
  const [historySearch, setHistorySearch] = useState('');
  const [historyFilter, setHistoryFilter] = useState('all');
  const [historySortField, setHistorySortField] = useState('timestamp');
  const [historySortOrder, setHistorySortOrder] = useState('desc');
  const [historyStartDate, setHistoryStartDate] = useState('');
  const [historyEndDate, setHistoryEndDate] = useState('');

  // Theme state
  const [theme, setTheme] = useState(() => localStorage.getItem('soc-theme') || 'dark');

  // Victim machines tracking
  const [victimCounts, setVictimCounts] = useState({
    'Victim-Web': 0,
    'Victim-DB': 0,
    'Victim-File': 0
  });
  
  const [lastAttackTimes, setLastAttackTimes] = useState({
    'Victim-Web': 0,
    'Victim-DB': 0,
    'Victim-File': 0
  });

  // Sound generator
  const playCyberAlertSound = (frequency = 600, duration = 0.1) => {
    if (isAudioMuted) return;
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      
      osc.type = 'sine';
      osc.frequency.setValueAtTime(frequency, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(120, audioCtx.currentTime + duration);
      
      gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
      gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + duration);
      
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    } catch (e) {
      console.warn("AudioContext blocked or unsupported", e);
    }
  };

  const toggleAudio = () => {
    setIsAudioMuted(prev => {
      const newVal = !prev;
      if (!newVal) {
        // Small beep feedback when unmuting
        setTimeout(() => playCyberAlertSound(550, 0.08), 50);
      }
      return newVal;
    });
  };

  // Helper to resolve threat severity
  const getSeverity = (attackType) => {
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
  };

  // Toast adder
  const addToast = (alert) => {
    const toastId = Date.now() + Math.random().toString();
    const conf = parseFloat(alert.confidence).toFixed(1);
    
    const newToast = {
      id: toastId,
      title: `Alerte NIDS : ${alert.attack_type}`,
      message: `La machine ${alert.dst_machine || alert.dst_ip} (${alert.dst_service || 'Service Inconnu'}) subit une attaque.`,
      meta: `Source: ${alert.src_machine || alert.src_ip} | Conf. ${conf}%`,
      alert_id: alert.alert_id
    };

    setToasts(prev => [newToast, ...prev].slice(0, 5));

    // Play cyber notification beep
    playCyberAlertSound(780, 0.15);

    // Auto delete toast after 5s
    setTimeout(() => {
      removeToast(toastId);
    }, 5000);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // History sort toggling handler
  const handleHistorySort = (field) => {
    if (historySortField === field) {
      setHistorySortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setHistorySortField(field);
      setHistorySortOrder('desc');
    }
  };

  // Mock Alert trigger for demonstration/testing
  const handleTestAlert = () => {
    const mockAlert = {
      alert_id: 'mock-' + Math.random(),
      attack_type: 'SQL INJECTION ATTEMPT',
      timestamp: Date.now() / 1000,
      confidence: 96.4,
      src_ip: '192.168.1.105',
      src_machine: 'Kali-Attack',
      dst_ip: '10.0.0.12',
      dst_machine: 'Victim-Web',
      dst_service: 'apache2 (HTTP)'
    };

    // Add to lists
    setRecentAlerts(prev => [mockAlert, ...prev]);
    setHistoryAlerts(prev => [mockAlert, ...prev]);
    
    // Update threat time for victim cards to flash under-attack
    setLastAttackTimes(prev => ({
      ...prev,
      'Victim-Web': Date.now()
    }));

    // Trigger toast + audio pings
    addToast(mockAlert);
    
    if (activeSection !== 'monitoring') {
      setUnreadCount(c => c + 1);
    }
  };

  // Calculate Threat Level based on recent alerts ratio
  const calculateThreatLevel = (alerts) => {
    if (alerts.length === 0) return 'FAIBLE';
    const recentSample = alerts.slice(0, 15);
    const criticals = recentSample.filter(a => a.attack_type !== 'BENIGN');
    const ratio = criticals.length / recentSample.length;
    
    if (ratio > 0.7) return 'CRITIQUE';
    if (ratio > 0.3) return 'ÉLEVÉ';
    if (ratio > 0) return 'MOYEN';
    return 'FAIBLE';
  };

  // Theme bascule effect
  useEffect(() => {
    if (theme === 'light') {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('soc-theme', next);
      return next;
    });
  };

  // Simulating random inference latency (1.4 - 2.1 ms)
  useEffect(() => {
    const latInterval = setInterval(() => {
      const randLat = (Math.random() * 0.7 + 1.4).toFixed(2);
      setAvgLatency(randLat);
    }, 2000);
    return () => clearInterval(latInterval);
  }, []);

  // Sync WebSocket for real-time alerting
  useEffect(() => {
    let ws;
    let reconnectTimeout;

    function connect() {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setWsConnected(true);
        console.log("[WebSocket] Connection established to backend");
      };

      ws.onclose = () => {
        setWsConnected(false);
        console.log("[WebSocket] Connection closed. Retrying in 5 seconds...");
        reconnectTimeout = setTimeout(connect, 5000);
      };

      ws.onerror = (err) => {
        console.error("[WebSocket] Error occurred:", err);
      };

      ws.onmessage = (event) => {
        const alert = JSON.parse(event.data);

        // Add to caches
        setRecentAlerts(prev => {
          if (prev.some(a => a.alert_id === alert.alert_id)) return prev;
          const updated = [alert, ...prev].slice(0, 50);
          
          // Recalculate threat level
          const nextLevel = calculateThreatLevel(updated);
          setThreatLevel(nextLevel);
          return updated;
        });

        setHistoryAlerts(prev => {
          if (prev.some(a => a.alert_id === alert.alert_id)) return prev;
          return [alert, ...prev].slice(0, 100);
        });

        // Trigger active visual states on victims cards
        if (alert.attack_type !== 'BENIGN') {
          const machine = alert.dst_machine;
          if (machine && ['Victim-Web', 'Victim-DB', 'Victim-File'].includes(machine)) {
            setLastAttackTimes(prev => ({
              ...prev,
              [machine]: Date.now()
            }));
          }

          // Trigger toast alerting system
          addToast(alert);

          // Increment notification bell count
          if (activeSection !== 'monitoring') {
            setUnreadCount(c => c + 1);
          }
        }
      };
    }

    connect();

    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimeout);
    };
  }, [activeSection]);

  // REST API Pollers (Every 2.5 seconds)
  useEffect(() => {
    async function fetchData() {
      try {
        // 1. Fetch statistics
        const statsRes = await fetch(`${API_URL}/stats`);
        const stats = await statsRes.json();
        
        setTotalAlerts(stats.total_alerts || 0);
        
        // Critical alerts = Total - Benign
        const benignCount = stats.attack_distribution?.['BENIGN'] || 0;
        setCriticalAlerts((stats.total_alerts || 0) - benignCount);

        setVictimCounts(stats.machine_distribution || {
          'Victim-Web': 0,
          'Victim-DB': 0,
          'Victim-File': 0
        });

        // 2. Fetch recent alerts
        const recentRes = await fetch(`${API_URL}/alerts/recent?limit=100`);
        const recent = await recentRes.json();
        
        setRecentAlerts(recent.slice(0, 50));
        setHistoryAlerts(recent);

        // Update threat level
        const nextLevel = calculateThreatLevel(recent.slice(0, 50));
        setThreatLevel(nextLevel);

      } catch (err) {
        console.warn("NIDS SOC API polling error:", err);
      }
    }

    fetchData(); // Run instantly on mount
    const pollInterval = setInterval(fetchData, 10000);

    return () => clearInterval(pollInterval);
  }, []);

  return (
    <div className="dashboard-container">
      {/* Sidebar navigation */}
      <Sidebar 
        activeSection={activeSection} 
        setActiveSection={setActiveSection} 
        unreadCount={unreadCount}
        setUnreadCount={setUnreadCount}
        isAudioMuted={isAudioMuted}
        toggleAudio={toggleAudio}
      />

      {/* Main Panel Content */}
      <div className="main-wrapper">
        <header>
          <div className="header-left">
            <h1>
              {activeSection === 'monitoring' && 'Tableau de Bord SOC - Surveillance Directe'}
              {activeSection === 'history' && 'Historique Global des Flux'}
              {activeSection === 'threats' && 'Analyse Approfondie des Menaces'}
              {activeSection === 'settings' && 'Configuration Réseau'}
            </h1>
            <p>
              {activeSection === 'monitoring' && 'Surveillance active des flux réseau via Traffic Mirroring'}
              {activeSection === 'history' && 'Visualisation des détections conservées dans la base de données'}
              {activeSection === 'threats' && 'Rapports analytiques et évolution temporelle des signatures réseau'}
              {activeSection === 'settings' && 'Paramètres généraux du SOC et statut de Kali Linux'}
            </p>
          </div>

          <div className="header-right">
            <button 
              className="btn-icon" 
              onClick={toggleTheme} 
              title={`Basculer en mode ${theme === 'dark' ? 'clair' : 'sombre'}`}
              style={{ marginRight: '0.25rem' }}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>

            <button 
              id="audio-toggle" 
              className={`btn-icon ${isAudioMuted ? 'muted' : ''}`} 
              onClick={toggleAudio} 
              title="Activer/Désactiver l'alerte sonore"
            >
              {isAudioMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
            </button>

            <div id="ws-status-badge" className={`status-badge ${wsConnected ? 'connected' : 'disconnected'}`}>
              <div className="status-dot"></div>
              <span>{wsConnected ? 'ONLINE' : 'OFFLINE'}</span>
            </div>

            <div className="notification-bell" onClick={() => setActiveSection('monitoring')}>
              <Bell size={20} className="text-secondary" />
              {unreadCount > 0 && <span className="pulse-count">{unreadCount}</span>}
            </div>
          </div>
        </header>

        <main>
          {/* Section: Live Monitoring Dashboard */}
          <div className={`section-content ${activeSection === 'monitoring' ? 'active' : ''}`}>
            <StatsPanel 
              totalAlerts={totalAlerts}
              criticalAlerts={criticalAlerts}
              avgLatency={avgLatency}
              threatLevel={threatLevel}
            />

            <VictimsGrid 
              victimCounts={victimCounts}
              lastAttackTimes={lastAttackTimes}
            />

            <div className="dashboard-grid">
              <LiveFeed 
                alerts={recentAlerts}
                searchQuery={liveSearch}
                setSearchQuery={setLiveSearch}
                filterTarget={liveTarget}
                setFilterTarget={setLiveTarget}
                sortOrder={liveSort}
                setSortOrder={setLiveSort}
                getSeverity={getSeverity}
                startDate={liveStartDate}
                setStartDate={setLiveStartDate}
                endDate={liveEndDate}
                setEndDate={setLiveEndDate}
              />

              <div className="charts-container">
                <div className="chart-card glass">
                  <h3>Répartition des Attaques</h3>
                  <div className="chart-wrapper">
                    <AnalyticsMiniDoughnut history={historyAlerts} getSeverity={getSeverity} />
                  </div>
                </div>
                
                <div className="chart-card glass">
                  <h3>Cibles Visées</h3>
                  <div className="chart-wrapper">
                    <AnalyticsMiniBar victimCounts={victimCounts} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Section: Global DB History */}
          <div className={`section-content ${activeSection === 'history' ? 'active' : ''}`}>
            <HistoryTable 
              history={historyAlerts}
              searchQuery={historySearch}
              setSearchQuery={setHistorySearch}
              filterType={historyFilter}
              setFilterType={setHistoryFilter}
              sortField={historySortField}
              sortOrder={historySortOrder}
              onSort={handleHistorySort}
              getSeverity={getSeverity}
              startDate={historyStartDate}
              setStartDate={setHistoryStartDate}
              endDate={historyEndDate}
              setEndDate={setHistoryEndDate}
            />
          </div>

          {/* Section: Advanced Analytics Chart panels */}
          <div className={`section-content ${activeSection === 'threats' ? 'active' : ''}`}>
            <AnalyticsTab 
              history={historyAlerts} 
              getSeverity={getSeverity}
            />
          </div>

          {/* Section: Settings Tab */}
          <div className={`section-content ${activeSection === 'settings' ? 'active' : ''}`}>
            <SettingsTab 
              WS_URL={WS_URL}
              onTestAlert={handleTestAlert}
              isAudioMuted={isAudioMuted}
              toggleAudio={toggleAudio}
            />
          </div>
        </main>
      </div>

      {/* Slide-in toast alerts notifications floating deck */}
      <div id="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className="toast">
            <div className="toast-icon">
              <ShieldAlert size={18} />
            </div>
            <div className="toast-content">
              <div className="toast-title">{toast.title}</div>
              <div className="toast-message">{toast.message}</div>
              <div className="toast-meta">{toast.meta}</div>
            </div>
            <button className="toast-close" onClick={() => removeToast(toast.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// Inline Mini Charts to keep component structure clean and responsive inside App.jsx
function AnalyticsMiniDoughnut({ history, getSeverity }) {
  const canvasRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (canvasRef.current && history.length > 0) {
      const counts = {};
      history.forEach(a => {
        const type = a.attack_type || 'Unknown';
        counts[type] = (counts[type] || 0) + 1;
      });

      if (chartInstance.current) {
        chartInstance.current.destroy();
      }

      const ctx = canvasRef.current.getContext('2d');
      chartInstance.current = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: Object.keys(counts),
          datasets: [{
            data: Object.values(counts),
            backgroundColor: ['#00f0ff', '#ff2a5f', '#ffcc00', '#00ff94', '#a333ff'],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                color: '#94a3b8',
                boxWidth: 8,
                font: { size: 9 }
              }
            }
          }
        }
      });
    }

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [history]);

  return history.length === 0 ? (
    <div className="empty-state" style={{ padding: '2rem 0' }}>Aucune donnée</div>
  ) : (
    <canvas ref={canvasRef}></canvas>
  );
}

function AnalyticsMiniBar({ victimCounts }) {
  const canvasRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (canvasRef.current) {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }

      const ctx = canvasRef.current.getContext('2d');
      chartInstance.current = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: Object.keys(victimCounts),
          datasets: [{
            data: Object.values(victimCounts),
            backgroundColor: 'rgba(0, 240, 255, 0.45)',
            borderColor: '#00f0ff',
            borderWidth: 1.5,
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { 
              grid: { color: 'rgba(255, 255, 255, 0.03)' }, 
              ticks: { color: '#94a3b8', font: { size: 8 } } 
            },
            y: { 
              grid: { color: 'rgba(255, 255, 255, 0.03)' }, 
              ticks: { color: '#94a3b8', font: { size: 8 } }, 
              beginAtZero: true 
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [victimCounts]);

  return (
    <canvas ref={canvasRef}></canvas>
  );
}
