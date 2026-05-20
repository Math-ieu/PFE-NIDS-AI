import React from 'react';
import { Search, Shield, Info } from 'lucide-react';

export default function HistoryTable({ 
  history,
  searchQuery,
  setSearchQuery,
  filterType,
  setFilterType,
  sortField,
  sortOrder,
  onSort,
  getSeverity,
  startDate,
  setStartDate,
  endDate,
  setEndDate
}) {

  // Perform client-side filter and sorting
  const filteredHistory = React.useMemo(() => {
    let result = [...history];

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

    // Traffic type filter
    if (filterType === 'ATTACK') {
      result = result.filter(a => a.attack_type !== 'BENIGN');
    } else if (filterType === 'BENIGN') {
      result = result.filter(a => a.attack_type === 'BENIGN');
    }

    // Sort order
    result.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];
      
      if (sortField === 'confidence' || sortField === 'timestamp') {
        valA = parseFloat(valA) || 0;
        valB = parseFloat(valB) || 0;
      } else {
        valA = String(valA || "").toLowerCase();
        valB = String(valB || "").toLowerCase();
      }
      
      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [history, searchQuery, filterType, sortField, sortOrder, startDate, endDate]);

  const renderSortIndicator = (field) => {
    if (sortField !== field) {
      return <span style={{ color: 'var(--text-dim)' }}> ↕</span>;
    }
    return sortOrder === 'asc' ? 
      <span style={{ color: 'var(--primary)' }}> ↑</span> : 
      <span style={{ color: 'var(--primary)' }}> ↓</span>;
  };

  return (
    <div className="glass-panel glass" style={{ padding: '1.5rem' }}>
      <div className="container-header history-header">
        <h2>Historique Global des Détections (DynamoDB)</h2>
        <div className="filter-controls" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
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
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="all">Tous les flux</option>
            <option value="ATTACK">Attaques uniquement</option>
            <option value="BENIGN">Trafic Bénin</option>
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

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th 
                onClick={() => onSort('timestamp')} 
                className="sortable-header"
                style={{ width: '22%' }}
              >
                Horodatage{renderSortIndicator('timestamp')}
              </th>
              <th 
                onClick={() => onSort('attack_type')} 
                className="sortable-header"
                style={{ width: '25%' }}
              >
                Type d'Attaque{renderSortIndicator('attack_type')}
              </th>
              <th 
                onClick={() => onSort('src_ip')} 
                className="sortable-header"
                style={{ width: '18%' }}
              >
                Source IP{renderSortIndicator('src_ip')}
              </th>
              <th 
                onClick={() => onSort('dst_ip')} 
                className="sortable-header"
                style={{ width: '22%' }}
              >
                Destination IP{renderSortIndicator('dst_ip')}
              </th>
              <th 
                onClick={() => onSort('confidence')} 
                className="sortable-header"
                style={{ width: '13%' }}
              >
                Confiance{renderSortIndicator('confidence')}
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredHistory.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '4rem 0' }}>
                  <Info size={24} style={{ display: 'block', margin: '0 auto 0.75rem auto' }} />
                  Aucun flux enregistré ne correspond aux filtres.
                </td>
              </tr>
            ) : (
              filteredHistory.map((a) => {
                const sev = getSeverity(a.attack_type);
                const targetName = a.dst_machine || a.dst_ip;
                const targetServ = a.dst_service ? ` (${a.dst_service})` : "";
                const attackerName = a.src_machine || a.src_ip;

                // Format full date & time (DD/MM/YYYY HH:MM:SS)
                const timeStr = new Date(a.timestamp * 1000).toLocaleString('fr-FR', {
                  day: '2-digit',
                  month: '2-digit',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit'
                });

                return (
                  <tr key={a.alert_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{timeStr}</td>
                    <td>
                      <span className={`severity-badge ${sev.class}`}>
                        {sev.label} ({a.attack_type})
                      </span>
                    </td>
                    <td>{attackerName}</td>
                    <td>{targetName}{targetServ}</td>
                    <td style={{ 
                      fontFamily: 'var(--font-mono)', 
                      fontWeight: 'bold', 
                      color: 'var(--primary)' 
                    }}>
                      {parseFloat(a.confidence).toFixed(1)}%
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
