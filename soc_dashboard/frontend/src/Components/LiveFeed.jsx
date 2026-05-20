import React from 'react';
import { Search, Radio, ArrowRight, ShieldAlert } from 'lucide-react';

export default function LiveFeed({ 
  alerts,
  searchQuery, 
  setSearchQuery, 
  filterTarget, 
  setFilterTarget, 
  sortOrder, 
  setSortOrder,
  getSeverity,
  startDate,
  setStartDate,
  endDate,
  setEndDate
}) {
  
  // Apply filtering and sorting dynamically
  const filteredAlerts = React.useMemo(() => {
    let result = [...alerts];

    // Start date filter (from Date X)
    if (startDate) {
      const startMs = new Date(startDate + "T00:00:00").getTime() / 1000;
      result = result.filter(a => a.timestamp >= startMs);
    }

    // End date filter (to Date Y)
    if (endDate) {
      const endMs = new Date(endDate + "T23:59:59").getTime() / 1000;
      result = result.filter(a => a.timestamp <= endMs);
    }

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(a => {
        const attackType = (a.attack_type || "").toLowerCase();
        const srcIp = (a.src_ip || "").toLowerCase();
        const dstIp = (a.dst_ip || "").toLowerCase();
        const srcMac = (a.src_machine || "").toLowerCase();
        const dstMac = (a.dst_machine || "").toLowerCase();
        return attackType.includes(q) || 
               srcIp.includes(q) || 
               dstIp.includes(q) ||
               srcMac.includes(q) || 
               dstMac.includes(q);
      });
    }

    // Victim target filter
    if (filterTarget !== 'all') {
      result = result.filter(a => a.dst_machine === filterTarget);
    }

    // Sort order
    if (sortOrder === 'time-desc') {
      result.sort((a, b) => b.timestamp - a.timestamp);
    } else if (sortOrder === 'time-asc') {
      result.sort((a, b) => a.timestamp - b.timestamp);
    } else if (sortOrder === 'conf-desc') {
      result.sort((a, b) => parseFloat(b.confidence) - parseFloat(a.confidence));
    } else if (sortOrder === 'conf-asc') {
      result.sort((a, b) => parseFloat(a.confidence) - parseFloat(b.confidence));
    }

    return result.slice(0, 15); // Show only top 15 matches for live list
  }, [alerts, searchQuery, filterTarget, sortOrder, startDate, endDate]);

  return (
    <div className="alerts-container glass">
      <div className="container-header" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Flux d'Alertes en Direct</h2>
        <div className="filter-controls" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          <div className="search-box">
            <Search size={13} />
            <input 
              type="text" 
              placeholder="Rechercher IP/Attaque..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <select 
            className="glass-select"
            value={filterTarget}
            onChange={(e) => setFilterTarget(e.target.value)}
          >
            <option value="all">Toutes cibles</option>
            <option value="Victim-Web">Victim-Web</option>
            <option value="Victim-DB">Victim-DB</option>
            <option value="Victim-File">Victim-File</option>
          </select>

          <select 
            className="glass-select"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
          >
            <option value="time-desc">Plus Récents ↕</option>
            <option value="time-asc">Plus Anciens ↕</option>
            <option value="conf-desc">Confiance ↑</option>
            <option value="conf-asc">Confiance ↓</option>
          </select>

          <div className="date-filter-group" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>De</span>
            <input 
              type="date" 
              className="glass-select date-input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={{ padding: '0.35rem 0.5rem', minWidth: '115px' }}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>À</span>
            <input 
              type="date" 
              className="glass-select date-input"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={{ padding: '0.35rem 0.5rem', minWidth: '115px' }}
            />
            {(startDate || endDate) && (
              <button 
                onClick={() => { setStartDate(''); setEndDate(''); }}
                style={{
                  background: 'rgba(255, 42, 95, 0.1)',
                  border: '1px solid rgba(255, 42, 95, 0.25)',
                  color: 'var(--accent)',
                  borderRadius: '4px',
                  padding: '0.2rem 0.45rem',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  transition: 'all 0.2s ease'
                }}
                title="Effacer le filtre temporel"
              >
                ×
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="alerts-list-wrapper">
        {filteredAlerts.length === 0 ? (
          <div className="empty-state">
            <Radio size={32} />
            <p>Aucune alerte active dans le flux.</p>
          </div>
        ) : (
          filteredAlerts.map((a) => {
            const isCritical = a.attack_type !== 'BENIGN';
            const sev = getSeverity(a.attack_type);
            
            // Format full date & time (DD/MM/YYYY HH:MM:SS)
            const timeStr = new Date(a.timestamp * 1000).toLocaleString('fr-FR', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            });

            const confVal = parseFloat(a.confidence).toFixed(1);
            const victimName = a.dst_machine || a.dst_ip;
            const attackerName = a.src_machine || a.src_ip;
            const targetService = a.dst_service ? `(${a.dst_service})` : "";

            return (
              <div 
                key={a.alert_id} 
                className={`alert-item ${isCritical ? 'critical' : ''}`}
              >
                <div className={`severity-badge ${sev.class}`}>
                  {sev.label}
                </div>
                
                <div className="alert-info">
                  <div className="alert-main">
                    <span className="attack-name">{a.attack_type}</span>
                    <span className="attack-conf">{confVal}% conf.</span>
                  </div>
                  <div className="attack-path">
                    <span>{attackerName}</span>
                    <ArrowRight size={10} style={{ margin: '0 0.35rem', verticalAlign: 'middle', display: 'inline-block' }} />
                    <span>{victimName}</span>
                    <span style={{ fontSize: '0.7rem', opacity: 0.6, color: 'var(--text-muted)', marginLeft: '0.35rem' }}>
                      {targetService}
                    </span>
                  </div>
                </div>
                
                <div className="alert-time">
                  {timeStr}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
