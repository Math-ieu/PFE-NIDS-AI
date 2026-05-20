import React from 'react';
import { ShieldAlert, Activity, History, Shield, Settings, ChevronLeft, ChevronRight } from 'lucide-react';

export default function Sidebar({ 
  activeSection, 
  setActiveSection, 
  unreadCount, 
  setUnreadCount
}) {
  const [isCollapsed, setIsCollapsed] = React.useState(() => {
    return localStorage.getItem('soc-sidebar-collapsed') === 'true';
  });

  const handleToggleCollapse = () => {
    setIsCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('soc-sidebar-collapsed', String(next));
      return next;
    });
  };

  const handleNavClick = (section) => {
    setActiveSection(section);
    if (section === 'monitoring') {
      // Reset unread count when clicking on live monitoring
      setUnreadCount(0);
    }
  };

  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-toggle-container">
        <button 
          className="sidebar-toggle-btn"
          onClick={handleToggleCollapse}
          title={isCollapsed ? "Agrandir le menu" : "Réduire le menu"}
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <div className="logo-container">
        <div className="logo-icon">
          <ShieldAlert size={26} />
        </div>
        <div className="logo-text">AI-NIDS<span>.SOC</span></div>
      </div>

      <nav className="nav-menu">
        <ul>
          <li 
            className={`nav-item ${activeSection === 'monitoring' ? 'active' : ''}`}
            onClick={() => handleNavClick('monitoring')}
            style={{ listStyle: 'none' }}
            title={isCollapsed ? "Monitoring Live" : ""}
          >
            <Activity size={18} />
            <span>Monitoring Live</span>
          </li>
          <li 
            className={`nav-item ${activeSection === 'history' ? 'active' : ''}`}
            onClick={() => handleNavClick('history')}
            style={{ listStyle: 'none' }}
            title={isCollapsed ? "Historique SQS" : ""}
          >
            <History size={18} />
            <span>Historique SQS</span>
          </li>
          <li 
            className={`nav-item ${activeSection === 'threats' ? 'active' : ''}`}
            onClick={() => handleNavClick('threats')}
            style={{ listStyle: 'none' }}
            title={isCollapsed ? "Analyse Menaces" : ""}
          >
            <Shield size={18} />
            <span>Analyse Menaces</span>
          </li>
          <li 
            className={`nav-item ${activeSection === 'settings' ? 'active' : ''}`}
            onClick={() => handleNavClick('settings')}
            style={{ listStyle: 'none' }}
            title={isCollapsed ? "Configuration" : ""}
          >
            <Settings size={18} />
            <span>Configuration</span>
          </li>
        </ul>
      </nav>

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="avatar">AN</div>
          <div className="user-details">
            <span className="user-name">Admin NIDS</span>
            <span className="user-role">SOC Operator</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
