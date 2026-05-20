import React from 'react';
import { Terminal, Shield, Cpu, RefreshCw, Volume2, VolumeX } from 'lucide-react';

export default function SettingsTab({ 
  WS_URL, 
  onTestAlert, 
  isAudioMuted, 
  toggleAudio 
}) {
  return (
    <div className="settings-grid">
      <div className="settings-card glass">
        <div className="container-header">
          <h3>
            <Shield size={18} style={{ color: 'var(--primary)', verticalAlign: 'middle', marginRight: '0.5rem' }} />
            <span>Infrastructure Cyberrange AWS</span>
          </h3>
        </div>
        
        <div className="settings-row">
          <div className="label">
            <span className="label-title">Statut NIDS Backend</span>
            <span className="label-desc">Port de l'API REST de monitoring</span>
          </div>
          <span className="settings-value">FastAPI (Port 8001)</span>
        </div>

        <div className="settings-row">
          <div className="label">
            <span className="label-title">Canal WebSocket Push</span>
            <span className="label-desc">URL d'écoute en direct</span>
          </div>
          <span className="settings-value" style={{ fontSize: '0.75rem' }}>{WS_URL}</span>
        </div>

        <div className="settings-row">
          <div className="label">
            <span className="label-title">Région AWS Actives</span>
            <span className="label-desc">Hébergement des instances EC2</span>
          </div>
          <span className="settings-value">eu-west-1 (Ireland)</span>
        </div>

        <div className="settings-row">
          <div className="label">
            <span className="label-title">Base de Stockage DynamoDB</span>
            <span className="label-desc">Table pour l'historique global</span>
          </div>
          <span className="settings-value">NIDS-Alerts</span>
        </div>
      </div>

      <div className="settings-card glass">
        <div className="container-header">
          <h3>
            <Terminal size={18} style={{ color: 'var(--accent)', verticalAlign: 'middle', marginRight: '0.5rem' }} />
            <span>Kali-Attack & Outils Opérationnels</span>
          </h3>
        </div>

        <div className="settings-row">
          <div className="label">
            <span className="label-title">Avertisseur Sonore</span>
            <span className="label-desc">Bips lors d'attaques critiques</span>
          </div>
          <button 
            className={`btn-icon ${isAudioMuted ? 'muted' : ''}`}
            onClick={toggleAudio}
            style={{ width: 'auto', height: 'auto', padding: '0.4rem 0.8rem', display: 'flex', gap: '0.4rem', fontSize: '0.75rem' }}
          >
            {isAudioMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
            <span>{isAudioMuted ? 'Désactivé' : 'Activé'}</span>
          </button>
        </div>

        <div className="settings-row">
          <div className="label">
            <span className="label-title">Simulation d'Alerte</span>
            <span className="label-desc">Déclencher un ping de test dans le SOC</span>
          </div>
          <button 
            className="cyber-btn"
            onClick={onTestAlert}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem' }}
          >
            <RefreshCw size={13} />
            <span>Tester Alerte</span>
          </button>
        </div>

        <div className="settings-row">
          <div className="label">
            <span className="label-title">Machine Kali Linux AWS</span>
            <span className="label-desc">Serveur d'attaque avec interface GUI</span>
          </div>
          <span className="settings-value" style={{ color: 'var(--accent)' }}>Kali-Attack (Active)</span>
        </div>

        <div className="settings-row">
          <div className="label">
            <span className="label-title">Accès Bureau à Distance</span>
            <span className="label-desc">Kali Linux RDP Access</span>
          </div>
          <span className="settings-value">Port 3389 (xrdp)</span>
        </div>
      </div>
    </div>
  );
}
