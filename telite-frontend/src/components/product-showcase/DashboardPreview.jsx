import "./DashboardPreview.css";

const tenants = [
  { name: "IIT Bombay", status: "Healthy", learners: "12,400", sync: "99.9%", health: 100, tone: "success" },
  { name: "EduBridge Corp", status: "Degraded", learners: "8,100", sync: "84.2%", health: 65, tone: "warning" },
  { name: "NovaTech Inst", status: "Healthy", learners: "4,200", sync: "99.8%", health: 98, tone: "success" },
];

const uptimeBars = [96, 99, 98, 97, 99, 100, 99, 97, 98, 100, 100, 99];

export default function DashboardPreview() {
  return (
    <div className="dashboard-preview">
      <div className="admin-status-bar">
        <div className="status-item">
          <span className="dot healthy"></span>
          IIT Bombay: Active
        </div>
        <div className="status-item">
          <span className="dot warning"></span>
          EduBridge: Syncing Queue
        </div>
        <div className="admin-id">Admin: Global Cluster 01 | Updated 32s ago</div>
      </div>

      <div className="dashboard-grid">
        <div className="dash-card tenant-health">
          <div className="card-header">
            <span className="dash-label">Active Tenants</span>
            <span className="total-count">Total: 42</span>
          </div>
          <div className="tenant-list">
            {tenants.map((tenant) => (
              <div key={tenant.name} className="tenant-row">
                <div className="tenant-info">
                  <div className="tenant-main">
                    <span className="tenant-name">{tenant.name}</span>
                    <div className="health-mini-bar">
                      <div className={`tone-${tenant.tone}`} style={{ width: `${tenant.health}%` }} />
                    </div>
                  </div>
                  <span className={`tenant-status tone-${tenant.tone}`}>{tenant.status}</span>
                </div>
                <div className="tenant-metrics">
                  <div className="metric-group">
                    <small>LEARNERS</small>
                    <span>{tenant.learners}</span>
                  </div>
                  <div className="metric-group">
                    <small>SYNC</small>
                    <span className={`sync-pill tone-${tenant.tone}`}>{tenant.sync}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="ops-column">
          <div className="dash-card uptime-widget">
            <span className="dash-label">Global Availability</span>
            <div className="uptime-value">99.998%</div>
            <div className="uptime-graph">
              {uptimeBars.map((value, index) => (
                <div key={index} className="uptime-bar" style={{ height: `${value}%` }} />
              ))}
            </div>
          </div>

          <div className="dash-card active-sessions">
             <span className="dash-label">Active Global Sessions</span>
             <div className="session-stats">
                <div className="stat">
                  <span className="val">24.1k</span>
                  <small>CURRENT</small>
                </div>
                <div className="stat">
                  <span className="val">1.2s</span>
                  <small>AVG LATENCY</small>
                </div>
                <div className="stat">
                  <span className="val">318</span>
                  <small>QUEUE DEPTH</small>
                </div>
             </div>
          </div>
        </div>

        <div className="dash-card sys-health">
          <span className="dash-label">Security & Ops Events</span>
          <div className="event-list">
            <div className="alert-item high">
              <div className="alert-meta">
                <span className="alert-time">10:42 AM</span>
                <span className="severity">CRITICAL</span>
              </div>
              <span className="alert-txt">Moodle sync timeout detected for Cluster-B</span>
            </div>
            <div className="alert-item med">
              <div className="alert-meta">
                <span className="alert-time">09:15 AM</span>
                <span className="severity">INFO</span>
              </div>
              <span className="alert-txt">New enterprise tenant 'FinEdge' onboarded.</span>
            </div>
            <div className="alert-item low">
              <div className="alert-meta">
                <span className="alert-time">08:02 AM</span>
                <span className="severity">STABLE</span>
              </div>
              <span className="alert-txt">Automatic DB optimization completed.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
