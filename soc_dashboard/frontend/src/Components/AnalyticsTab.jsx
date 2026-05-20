import React, { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';

export default function AnalyticsTab({ history, getSeverity }) {
  const timelineCanvasRef = useRef(null);
  const severityCanvasRef = useRef(null);
  const serviceCanvasRef = useRef(null);

  const timelineChartInstance = useRef(null);
  const severityChartInstance = useRef(null);
  const serviceChartInstance = useRef(null);

  const historyRef = useRef(history);
  const getSeverityRef = useRef(getSeverity);

  // Keep refs in sync with incoming props
  useEffect(() => {
    historyRef.current = history;
  }, [history]);

  useEffect(() => {
    getSeverityRef.current = getSeverity;
  }, [getSeverity]);

  const renderCharts = () => {
    const currentHistory = historyRef.current;
    const currentGetSeverity = getSeverityRef.current;
    if (!currentHistory || currentHistory.length === 0) return;

    // 1. TIMELINE CHART (Attack frequency per minute)
    if (timelineCanvasRef.current) {
      const timelineCounts = {};
      currentHistory.forEach(a => {
        const date = new Date(a.timestamp * 1000);
        const timeStr = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        timelineCounts[timeStr] = (timelineCounts[timeStr] || 0) + 1;
      });
      
      const sortedMinutes = Object.keys(timelineCounts).sort().slice(-15);
      const timelineValues = sortedMinutes.map(m => timelineCounts[m]);

      if (timelineChartInstance.current) {
        timelineChartInstance.current.destroy();
      }

      const ctx = timelineCanvasRef.current.getContext('2d');
      timelineChartInstance.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels: sortedMinutes,
          datasets: [{
            label: 'Alertes par minute',
            data: timelineValues,
            borderColor: '#00f0ff',
            backgroundColor: 'rgba(0, 240, 255, 0.08)',
            borderWidth: 2,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#00f0ff',
            pointBorderColor: '#fff',
            pointHoverRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { 
              grid: { color: 'rgba(255, 255, 255, 0.03)' }, 
              ticks: { color: '#94a3b8', font: { size: 9, family: 'Inter' } } 
            },
            y: { 
              grid: { color: 'rgba(255, 255, 255, 0.03)' }, 
              ticks: { color: '#94a3b8', font: { size: 9, family: 'Inter' }, stepSize: 1 }, 
              beginAtZero: true 
            }
          },
          plugins: { 
            legend: { display: false } 
          }
        }
      });
    }

    // 2. SEVERITY CHART (Doughnut)
    if (severityCanvasRef.current) {
      const severityCounts = { INFO: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
      currentHistory.forEach(a => {
        const sev = currentGetSeverity(a.attack_type);
        severityCounts[sev.code]++;
      });

      if (severityChartInstance.current) {
        severityChartInstance.current.destroy();
      }

      const ctx = severityCanvasRef.current.getContext('2d');
      severityChartInstance.current = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Bénigne (Info)', 'Moyenne', 'Élevée', 'Critique'],
          datasets: [{
            data: [
              severityCounts.INFO,
              severityCounts.MEDIUM,
              severityCounts.HIGH,
              severityCounts.CRITICAL
            ],
            backgroundColor: ['#00ff94', '#ffcc00', '#a333ff', '#ff2a5f'],
            borderWidth: 0,
            hoverOffset: 4
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
                boxWidth: 12, 
                font: { size: 10, family: 'Inter' } 
              } 
            }
          }
        }
      });
    }

    // 3. SERVICES TARGET CHART (Polar Area)
    if (serviceCanvasRef.current) {
      const serviceCounts = {};
      currentHistory.forEach(a => {
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

      if (serviceChartInstance.current) {
        serviceChartInstance.current.destroy();
      }

      const ctx = serviceCanvasRef.current.getContext('2d');
      serviceChartInstance.current = new Chart(ctx, {
        type: 'polarArea',
        data: {
          labels: Object.keys(serviceCounts),
          datasets: [{
            data: Object.values(serviceCounts),
            backgroundColor: [
              'rgba(0, 240, 255, 0.35)',
              'rgba(163, 51, 255, 0.35)',
              'rgba(255, 204, 0, 0.35)',
              'rgba(0, 255, 148, 0.35)',
              'rgba(255, 42, 95, 0.35)'
            ],
            borderColor: [
              '#00f0ff',
              '#a333ff',
              '#ffcc00',
              '#00ff94',
              '#ff2a5f'
            ],
            borderWidth: 1.5
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              grid: { color: 'rgba(255, 255, 255, 0.03)' },
              angleLines: { color: 'rgba(255, 255, 255, 0.03)' },
              ticks: { display: false }
            }
          },
          plugins: {
            legend: { 
              position: 'bottom', 
              labels: { 
                color: '#94a3b8', 
                boxWidth: 10, 
                font: { size: 9, family: 'Inter' } 
              } 
            }
          }
        }
      });
    }
  };

  // Immediate draw when history becomes available and charts not loaded
  useEffect(() => {
    if (history.length > 0 && !timelineChartInstance.current) {
      renderCharts();
    }
  }, [history]);

  // Stable 10s refresh interval
  useEffect(() => {
    const interval = setInterval(() => {
      renderCharts();
    }, 10000);

    return () => {
      clearInterval(interval);
      if (timelineChartInstance.current) timelineChartInstance.current.destroy();
      if (severityChartInstance.current) severityChartInstance.current.destroy();
      if (serviceChartInstance.current) serviceChartInstance.current.destroy();
    };
  }, []);

  return (
    <div className="analytics-grid">
      <div className="analytics-card glass wide-card">
        <div className="container-header">
          <div>
            <h3>Évolution Temporelle des Attaques (Flux SQS)</h3>
            <span className="chart-subtitle">Volume de détections réseau par minute</span>
          </div>
        </div>
        <div className="chart-wrapper large-chart">
          {history.length === 0 ? (
            <div className="empty-state">En attente de données historiques...</div>
          ) : (
            <canvas ref={timelineCanvasRef}></canvas>
          )}
        </div>
      </div>

      <div className="analytics-card glass">
        <div className="container-header">
          <h3>Distribution des Sévérités</h3>
        </div>
        <div className="chart-wrapper">
          {history.length === 0 ? (
            <div className="empty-state">En attente de données...</div>
          ) : (
            <canvas ref={severityCanvasRef}></canvas>
          )}
        </div>
      </div>

      <div className="analytics-card glass">
        <div className="container-header">
          <h3>Services Visés</h3>
        </div>
        <div className="chart-wrapper">
          {history.length === 0 ? (
            <div className="empty-state">En attente de données...</div>
          ) : (
            <canvas ref={serviceCanvasRef}></canvas>
          )}
        </div>
      </div>
    </div>
  );
}
