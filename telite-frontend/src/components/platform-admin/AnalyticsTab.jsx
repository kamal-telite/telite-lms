import { useState, useEffect, useMemo } from "react";
import { useToast } from "../../components/common/ui";
import { downloadCSV } from "../../utils/csvExport";

export default function AnalyticsTab({ searchQuery }) {
  const { showToast } = useToast();
  const [chartPeriod, setChartPeriod] = useState("monthly");
  const [liveMonitorActive, setLiveMonitorActive] = useState(false);
  const [healthFilter, setHealthFilter] = useState("all");
  const [filterPopoverOpen, setFilterPopoverOpen] = useState(false);
  const [alertOrg, setAlertOrg] = useState(null);
  
  const [barChartData, setBarChartData] = useState([
    { label: 'JAN', val: 32 }, { label: 'FEB', val: 41 }, { label: 'MAR', val: 58 },
    { label: 'APR', val: 50 }, { label: 'MAY', val: 74 }, { label: 'JUN', val: 89 }
  ]);

  const monthlyData = [
    { label: 'JAN', val: 32 }, { label: 'FEB', val: 41 }, { label: 'MAR', val: 58 },
    { label: 'APR', val: 50 }, { label: 'MAY', val: 74 }, { label: 'JUN', val: 89 }
  ];
  const weeklyData = [
    { label: 'W1', val: 18 }, { label: 'W2', val: 25 }, { label: 'W3', val: 22 },
    { label: 'W4', val: 31 }, { label: 'W5', val: 28 }, { label: 'W6', val: 35 }
  ];

  useEffect(() => {
    if (!liveMonitorActive) {
      setBarChartData(chartPeriod === 'weekly' ? weeklyData : monthlyData);
    }
  }, [chartPeriod, liveMonitorActive, monthlyData, weeklyData]);

  useEffect(() => {
    let interval = null;
    if (liveMonitorActive) {
      interval = setInterval(() => {
        setBarChartData(current => current.map(item => {
          const delta = Math.floor(Math.random() * 20 - 10);
          const newVal = Math.max(10, Math.min(120, item.val + delta));
          return { ...item, val: newVal };
        }));
      }, 2000);
      showToast('Live monitor activated — updating every 2s', 'success');
    } else if (interval) {
      clearInterval(interval);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [liveMonitorActive, showToast]);

  const handlePeriodChange = (e) => {
    setChartPeriod(e.target.value);
  };

  const toggleLiveMonitor = () => {
    setLiveMonitorActive(prev => {
      if (prev) showToast('Live monitor stopped', 'info');
      return !prev;
    });
  };

  const [donutSegment, setDonutSegment] = useState({ label: "CORP", pct: "64%" });
  const highlightSegment = (type, pct) => {
    setDonutSegment({ label: type.toUpperCase(), pct });
  };

  const initialAnalyticsOrgs = [
    { id: 'NV', name: 'Nexus Ventures', plan: 'Premium Plan', users: 2450, storageUsed: 750, storageTotal: 1000, health: 'Excellent', color: '#4F46E5' },
    { id: 'AU', name: 'Apex University', plan: 'Edu Enterprise', users: 4812, storageUsed: 2200, storageTotal: 5000, health: 'Stable', color: '#2563EB' },
    { id: 'SL', name: 'Skyline Logistics', plan: 'Standard Plan', users: 890, storageUsed: 460, storageTotal: 500, health: 'Warning', color: '#D97706' },
    { id: 'TU', name: 'Telite University', plan: 'Enterprise', users: 46, storageUsed: 12, storageTotal: 100, health: 'Excellent', color: '#4648D4' },
    { id: 'TS', name: 'Telite Systems', plan: 'Enterprise', users: 0, storageUsed: 2, storageTotal: 100, health: 'Stable', color: '#059669' },
  ];

  const filteredOrgs = useMemo(() => {
    let result = initialAnalyticsOrgs;
    if (healthFilter !== 'all') {
      result = result.filter(o => o.health.toLowerCase() === healthFilter.toLowerCase());
    }
    if (searchQuery && searchQuery.length >= 2) {
      const q = searchQuery.toLowerCase();
      result = result.filter(o => o.name.toLowerCase().includes(q) || o.plan.toLowerCase().includes(q));
    }
    return result;
  }, [healthFilter, searchQuery, initialAnalyticsOrgs]);

  const [activeMenuId, setActiveMenuId] = useState(null);
  const toggleRowMenu = (orgId) => {
    setActiveMenuId(prev => prev === orgId ? null : orgId);
  };

  const handleExportCSV = (org = null) => {
    showToast(org ? `Generating CSV report for ${org.name}…` : 'Generating CSV report…', 'info');
    setTimeout(() => {
      const headers = ['Organization', 'Plan', 'Active Users', 'Storage Used', 'Health'];
      const orgsToExport = org ? [org] : initialAnalyticsOrgs;
      const rows = orgsToExport.map(o => [o.name, o.plan, o.users, `${o.storageUsed}GB/${o.storageTotal}GB`, o.health]);
      downloadCSV(rows, headers, org ? `analytics-${org.id.toLowerCase()}.csv` : 'platform-analytics.csv');
      showToast('Analytics report downloaded successfully', 'success');
    }, 1200);
  };

  const maxVal = Math.max(...barChartData.map(d => d.val), 1);

  return (
    <div className="page" style={{ display: 'block' }}>
      <div className="page-header">
        <div>
          <div className="page-title">Platform Analytics</div>
          <div className="page-sub">Monitor real-time user growth, organizational distribution, and detailed engagement metrics.</div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={() => handleExportCSV()}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>download</span> Export CSV
          </button>
          <button 
            className="btn" 
            style={{ 
              backgroundColor: liveMonitorActive ? 'var(--green)' : 'var(--primary)',
              color: '#fff'
            }} 
            onClick={toggleLiveMonitor}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '15px', animation: liveMonitorActive ? 'spin 1.5s linear infinite' : 'none' }}>
              {liveMonitorActive ? 'sync' : 'monitor_heart'}
            </span> 
            {liveMonitorActive ? 'Live: ON' : 'Live Monitor'}
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '20px', overflow: 'hidden' }}>
        <div style={{ padding: '20px 24px', borderRight: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Total Active Users</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--fm)', letterSpacing: '-.5px' }}>12,482</div>
          <div style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '13px' }}>trending_up</span>+14%
          </div>
        </div>
        <div style={{ padding: '20px 24px', borderRight: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Daily Completion Rate</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--fm)', letterSpacing: '-.5px' }}>78.4%</div>
          <div style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '13px' }}>trending_up</span>+2%
          </div>
        </div>
        <div style={{ padding: '20px 24px', borderRight: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>Avg. Session Time</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)', letterSpacing: '-.5px' }}>42m</div>
          <div style={{ fontSize: '11px', color: 'var(--red)', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '13px' }}>trending_down</span>-5%
          </div>
        </div>
        <div style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', fontWeight: 500, marginBottom: '6px' }}>New Organizations</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--fm)', letterSpacing: '-.5px' }}>24</div>
          <div style={{ fontSize: '11px', color: 'var(--primary)', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '13px' }}>calendar_today</span>This Month
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '16px', marginBottom: '20px' }}>
        <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)' }}>User Growth Trend</div>
              <div style={{ fontSize: '12px', color: 'var(--tx2)', marginTop: '2px' }}>Last 6 months performance</div>
            </div>
            <select className="field-select" style={{ width: '110px', height: '30px', fontSize: '12px' }} value={chartPeriod} onChange={handlePeriodChange}>
              <option value="monthly">Monthly</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>
          <div style={{ position: 'relative', height: '200px', display: 'flex', alignItems: 'flex-end', gap: '10px', padding: '0 8px' }}>
            {barChartData.map((d, i) => (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', cursor: 'pointer', textAlign: 'center' }} onClick={() => showToast(`${d.label}: ${d.val} users`, 'info')}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tx2)' }}>{d.val}</div>
                <div className="bar-col" style={{ width: '100%', height: `${Math.round((d.val / maxVal) * 150)}px`, background: 'var(--primary)', borderRadius: '5px 5px 0 0' }}></div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '10px', padding: '0 8px', marginTop: '6px' }}>
            {barChartData.map((d, i) => (
              <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: '11px', fontWeight: 600, color: 'var(--tx3)', letterSpacing: '.06em' }}>{d.label}</div>
            ))}
          </div>
        </div>

        <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px' }}>
          <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)', marginBottom: '4px' }}>Org Distribution</div>
          <div style={{ fontSize: '12px', color: 'var(--tx2)', marginBottom: '16px' }}>Market segment breakdown</div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ position: 'relative', width: '140px', height: '140px', marginBottom: '16px' }}>
              <svg viewBox="0 0 140 140" style={{ transform: 'rotate(-90deg)' }}>
                <circle cx="70" cy="70" r="50" fill="none" stroke="#E5E7EB" strokeWidth="22" />
                <circle cx="70" cy="70" r="50" fill="none" stroke="#4648D4" strokeWidth="22" strokeDasharray="201 314" strokeLinecap="round" />
                <circle cx="70" cy="70" r="50" fill="none" stroke="#A5B4FC" strokeWidth="22" strokeDasharray="69 314" strokeDashoffset="-201" />
                <circle cx="70" cy="70" r="50" fill="none" stroke="#E0E7FF" strokeWidth="22" strokeDasharray="44 314" strokeDashoffset="-270" />
              </svg>
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', textAlign: 'center' }}>
                <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--tx1)', fontFamily: 'var(--fm)' }}>{donutSegment.pct}</div>
                <div style={{ fontSize: '10px', color: 'var(--tx2)', fontWeight: 600, letterSpacing: '.05em' }}>{donutSegment.label}</div>
              </div>
            </div>
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div className="donut-legend-item" onClick={() => highlightSegment('corp', '64%')} style={{ cursor: 'pointer' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#4648D4', flexShrink: 0 }}></span>
                <span style={{ fontSize: '12px', color: 'var(--tx1)', flex: 1 }}>Corporate</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--tx2)', fontFamily: 'var(--fm)' }}>64%</span>
              </div>
              <div className="donut-legend-item" onClick={() => highlightSegment('ed', '22%')} style={{ cursor: 'pointer' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#A5B4FC', flexShrink: 0 }}></span>
                <span style={{ fontSize: '12px', color: 'var(--tx1)', flex: 1 }}>Higher Ed</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--tx2)', fontFamily: 'var(--fm)' }}>22%</span>
              </div>
              <div className="donut-legend-item" onClick={() => highlightSegment('gov', '14%')} style={{ cursor: 'pointer' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#C7D2FE', flexShrink: 0 }}></span>
                <span style={{ fontSize: '12px', color: 'var(--tx1)', flex: 1 }}>Government</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--tx2)', fontFamily: 'var(--fm)' }}>14%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--tx1)' }}>Organization Usage</div>
            <div style={{ fontSize: '12px', color: 'var(--tx2)', marginTop: '2px' }}>Storage and user metrics by organization</div>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <select className="field-select" style={{ height: '32px', fontSize: '12px' }} value={healthFilter} onChange={e => setHealthFilter(e.target.value)}>
              <option value="all">All Health</option>
              <option value="excellent">Excellent</option>
              <option value="stable">Stable</option>
              <option value="warning">Warning</option>
            </select>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Organization</th>
              <th>Plan</th>
              <th>Active Users</th>
              <th>Storage</th>
              <th>Health</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredOrgs.map(org => (
              <tr key={org.id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div className="avatar" style={{ background: `${org.color}22`, color: org.color, fontSize: '12px' }}>
                      {org.name.substring(0, 2).toUpperCase()}
                    </div>
                    <span style={{ fontWeight: 600, fontSize: '13px' }}>{org.name}</span>
                  </div>
                </td>
                <td style={{ fontSize: '12px', color: 'var(--tx2)' }}>{org.plan}</td>
                <td style={{ fontFamily: 'var(--fm)', fontSize: '13px' }}>{org.users.toLocaleString()}</td>
                <td>
                  <div style={{ fontSize: '12px', fontFamily: 'var(--fm)' }}>{org.storageUsed}GB / {org.storageTotal}GB</div>
                  <div style={{ height: '4px', background: '#E5E7EB', borderRadius: '2px', marginTop: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', background: org.color, width: `${(org.storageUsed / org.storageTotal) * 100}%` }}></div>
                  </div>
                </td>
                <td>
                  <span className={`status-dot ${org.health.toLowerCase() === 'excellent' ? 'active' : org.health.toLowerCase() === 'warning' ? 'suspended' : 'active'}`}>
                    {org.health}
                  </span>
                </td>
                <td>
                  <button className="btn-icon btn" onClick={() => handleExportCSV(org)} title="Download CSV">
                    <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>download</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
