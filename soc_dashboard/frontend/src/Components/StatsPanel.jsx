import React from 'react';
import { Activity, ShieldAlert, Cpu, ShieldCheck, Flame } from 'lucide-react';

export default function StatsPanel({ 
  totalAlerts, 
  criticalAlerts, 
  avgLatency, 
  threatLevel 
}) {
  
  // Decide color and icon for the threat level card dynamically
  const getThreatCardDetails = () => {
    switch (threatLevel) {
      case 'CRITIQUE':
        return {
          colorClass: 'red',
          icon: <Flame size={20} className="pulse-danger" />,
          label: 'CRITIQUE'
        };
      case 'ÉLEVÉ':
        return {
          colorClass: 'purple',
          icon: <ShieldAlert size={20} />,
          label: 'ÉLEVÉ'
        };
      case 'MOYEN':
        return {
          colorClass: 'yellow',
          icon: <ShieldAlert size={20} />,
          label: 'MOYEN'
        };
      case 'FAIBLE':
      default:
        return {
          colorClass: 'green',
          icon: <ShieldCheck size={20} />,
          label: 'FAIBLE'
        };
    }
  };

  const threatDetails = getThreatCardDetails();

  return (
    <div className="stats-grid">
      <div className="stat-card glass">
        <div className="card-icon blue">
          <Activity size={20} />
        </div>
        <div className="card-info">
          <h3>Flux Réseau Analysés</h3>
          <div className="value">{totalAlerts.toLocaleString()}</div>
        </div>
      </div>

      <div className="stat-card glass">
        <div className="card-icon red">
          <ShieldAlert size={20} />
        </div>
        <div className="card-info">
          <h3>Attaques Critiques</h3>
          <div className="value">{criticalAlerts.toLocaleString()}</div>
        </div>
      </div>

      <div className="stat-card glass">
        <div className="card-icon purple">
          <Cpu size={20} />
        </div>
        <div className="card-info">
          <h3>Latence d'Inférence</h3>
          <div className="value">{avgLatency} ms</div>
        </div>
      </div>

      <div className="stat-card glass">
        <div className={`card-icon ${threatDetails.colorClass}`}>
          {threatDetails.icon}
        </div>
        <div className="card-info">
          <h3>Niveau de Menace</h3>
          <div className="value">{threatDetails.label}</div>
        </div>
      </div>
    </div>
  );
}
