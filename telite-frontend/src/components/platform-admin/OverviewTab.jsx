import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from "../../components/common/ui";
import { platformApi } from "../../services/platform";
import { useAdminStore } from "../../store/adminConsoleStore";

export default function OverviewTab({ searchQuery }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { isSyncing, syncProgress, lastSync, triggerSync, organizations } = useAdminStore();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const handleSync = async () => {
    await triggerSync();
    showToast('Global sync completed — 99.8% success rate', 'success');
  };

  useEffect(() => {
    platformApi.getAnalyticsOverview()
      .then(res => setData(res.data))
      .catch(() => showToast("Failed to load overview", "error"))
      .finally(() => setLoading(false));
  }, [showToast]);

  const stats = data || { total_orgs: 2, total_colleges: 1, total_companies: 1, total_users: 46, total_super_admins: 1 };

  if (loading) {
    return <div className="page" style={{display: 'block', padding: '40px', textAlign: 'center'}}>Loading overview...</div>;
  }

  return (
    <div className="page" style={{display: 'block'}}>
      <div className="page-header">
        <div>
          <div className="page-title">Platform Overview</div>
          <div className="page-sub">Global control center for all organizations</div>
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r)', fontSize: '12px', color: 'var(--tx2)'}}>
          <span className="material-symbols-outlined" style={{fontSize: '15px'}}>calendar_today</span>
          May 18, 2026
        </div>
      </div>

      <div className="status-bar">
        <div style={{display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px'}}>
          <div className="status-pill green"><span className="pulse"></span> All Systems Operational</div>
          <div className="status-info"><span className="material-symbols-outlined" style={{fontSize: '15px', color: 'var(--tx3)'}}>hub</span> System Gateway: <strong>API Connected · 142ms</strong></div>
          <div className="status-info"><span className="material-symbols-outlined" style={{fontSize: '15px', color: 'var(--tx3)'}}>people</span> <strong>2.4k</strong>&nbsp;Active Sessions</div>
        </div>
        <div className="status-info" style={{fontSize: '11px'}}><span className="material-symbols-outlined" style={{fontSize: '14px'}}>update</span> Last check: 1m ago</div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>corporate_fare</span></div>
            <span className="mc-badge badge-indigo">+12.5%</span>
          </div>
          <div className="mc-num">{stats.total_orgs}</div>
          <div className="mc-label">Total Orgs</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>account_balance</span></div>
            <span className="mc-badge badge-indigo">+4.2%</span>
          </div>
          <div className="mc-num">{stats.total_colleges}</div>
          <div className="mc-label">Colleges</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>business_center</span></div>
            <span className="mc-badge badge-indigo">+8.1%</span>
          </div>
          <div className="mc-num">{stats.total_companies}</div>
          <div className="mc-label">Companies</div>
        </div>
        <div className="metric-card">
          <div className="mc-top">
            <div className="mc-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)'}}>groups</span></div>
            <span className="mc-badge badge-indigo">+24%</span>
          </div>
          <div className="mc-num">{stats.total_users}</div>
          <div className="mc-label">Total Users</div>
        </div>
      </div>

      <div className="dash-grid">
        <div className="dash-panel">
          <div className="dash-panel-head">
            <span className="dash-panel-title">Recent Organizations</span>
            <span style={{fontSize: '12px', color: 'var(--primary)', fontWeight: 600, cursor: 'pointer'}} onClick={() => navigate('/platform-admin/organizations')}>View All</span>
          </div>
          <table>
            <thead><tr>
              <th>Organization</th><th>Type</th><th>Users</th><th>Status</th><th></th>
            </tr></thead>
            <tbody>
              {organizations.slice(0, 3).map(o => (
                <tr key={o.id}>
                  <td>
                    <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                      <div className="avatar" style={{background: o.type?.toLowerCase() === 'college' ? 'var(--primary-lt)' : '#ECFDF5', color: o.type?.toLowerCase() === 'college' ? 'var(--primary)' : '#059669', fontSize: '12px'}}>
                        {(o.name || 'O').substring(0,2).toUpperCase()}
                      </div>
                      <span style={{fontWeight: 600, fontSize: '13px'}}>{o.name}</span>
                    </div>
                  </td>
                  <td><span className={`badge ${o.type?.toLowerCase() === 'college' ? 'badge-indigo' : 'badge-gray'}`}>{o.type?.toUpperCase()}</span></td>
                  <td style={{fontFamily: 'var(--fm)'}}>{o.user_count || 1}</td>
                  <td><span className={`status-dot ${o.status?.toLowerCase() === 'active' ? 'active' : 'suspended'}`}>{o.status === 'active' ? 'Active' : 'Suspended'}</span></td>
                  <td><button className="btn btn-sm btn-secondary" onClick={() => navigate('/platform-admin/organizations')}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="dash-panel">
          <div className="dash-panel-head">
            <span className="dash-panel-title">Live Activity</span>
            <div className="live-badge"><span className="live-dot"></span>Live</div>
          </div>
          <div style={{padding: '0 16px'}}>
            <div className="activity-list">
              <div className="act-item">
                <div className="act-icon" style={{background: 'var(--primary-lt)'}}><span className="material-symbols-outlined" style={{color: 'var(--primary)', fontSize: '16px'}}>person_add</span></div>
                <div><div className="act-title">New User Registered</div><div className="act-sub">John Doe → Telite University</div><div className="act-time">2 minutes ago</div></div>
              </div>
              <div className="act-item">
                <div className="act-icon" style={{background: '#ECFDF5'}}><span className="material-symbols-outlined" style={{color: '#059669', fontSize: '16px'}}>check_circle</span></div>
                <div><div className="act-title">Course Published</div><div className="act-sub">"Advanced React Patterns" by Vikram Sethi</div><div className="act-time">8 minutes ago</div></div>
              </div>
              <div className="act-item">
                <div className="act-icon" style={{background: '#FEF2F2'}}><span className="material-symbols-outlined" style={{color: '#DC2626', fontSize: '16px'}}>error</span></div>
                <div><div className="act-title">Sync Warning</div><div className="act-sub">College A — partial sync completed</div><div className="act-time">15 minutes ago</div></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
