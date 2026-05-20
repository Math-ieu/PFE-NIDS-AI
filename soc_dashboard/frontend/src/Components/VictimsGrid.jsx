import React from 'react';
import { Globe, Database, FolderOpen, Shield, ShieldAlert } from 'lucide-react';

export default function VictimsGrid({ victimCounts, lastAttackTimes }) {
  const now = Date.now();

  const victims = [
    {
      id: 'Victim-Web',
      name: 'Victim-Web',
      ipLabel: 'Web Service',
      avatar: <Globe size={20} />,
      services: ['apache2 (HTTP)', 'PHP']
    },
    {
      id: 'Victim-DB',
      name: 'Victim-DB',
      ipLabel: 'Database Service',
      avatar: <Database size={20} />,
      services: ['mariadb (SQL)', 'redis']
    },
    {
      id: 'Victim-File',
      name: 'Victim-File',
      ipLabel: 'File Service',
      avatar: <FolderOpen size={20} />,
      services: ['samba (SMB)', 'vsftpd (FTP)']
    }
  ];

  return (
    <div style={{ marginBottom: '2.5rem' }}>
      <div className="victim-monitor-header">
        <h2>
          <ShieldAlert size={20} className="logo-icon" />
          <span>Cibles du Cyberrange AWS</span>
        </h2>
      </div>
      
      <div className="victim-grid">
        {victims.map((v) => {
          // Attack status decays after 15 seconds
          const isUnderAttack = now - (lastAttackTimes[v.id] || 0) < 15000;
          const count = victimCounts[v.id] || 0;

          return (
            <div 
              key={v.id} 
              id={`card-${v.id}`} 
              className={`victim-card glass ${isUnderAttack ? 'under-attack' : ''}`}
            >
              <div className="victim-status-container">
                <div className={`victim-status-dot ${isUnderAttack ? 'attacked' : 'safe'}`}></div>
                <span className={`victim-health ${isUnderAttack ? 'attacked' : 'safe'}`}>
                  {isUnderAttack ? 'SOUS ATTAQUE' : 'SÉCURISÉ'}
                </span>
              </div>

              <div className="victim-header">
                <div className="victim-avatar">
                  {v.avatar}
                </div>
                <div>
                  <h4 className="victim-name">{v.name}</h4>
                  <span className="victim-ip">{v.ipLabel}</span>
                </div>
              </div>

              <div className="victim-services">
                {v.services.map((svc, idx) => (
                  <span key={idx} className="badge">{svc}</span>
                ))}
              </div>

              <div className="victim-alert-stat">
                <span className="label">Alertes SQS:</span>
                <span className={`value count ${isUnderAttack ? 'threatened' : ''}`}>
                  {count}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
