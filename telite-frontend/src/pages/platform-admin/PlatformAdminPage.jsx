import React, { useEffect, useState, useMemo } from "react";
import { Route, Routes, useLocation, useNavigate, Link } from "react-router-dom";
import { useToast } from "../../components/common/ui";
import { platformApi } from "../../services/platform";
import "../../styles/platform-admin.css";

export default function PlatformAdminPage({ session, onLogout }) {
  const { pathname } = useLocation();

  const navGroups = [
    { section: "Core Section", items: [
      { id: "/platform-admin", icon: "grid_view", label: "Dashboard", exact: true },
      { id: "/platform-admin/organizations", icon: "corporate_fare", label: "Organizations" },
      { id: "/platform-admin/admins", icon: "admin_panel_settings", label: "Admin Control" },
    ]},
    { section: "Insights Section", items: [
      { id: "/platform-admin/moodle", icon: "sync", label: "Moodle Sync" },
      { id: "/platform-admin/analytics", icon: "insights", label: "Analytics" },
    ]},
    { section: "System Section", items: [
      { id: "/platform-admin/audit", icon: "list_alt", label: "Audit Logs" },
      { id: "/platform-admin/features", icon: "flag", label: "Feature Flags" },
      { id: "/platform-admin/settings", icon: "settings", label: "Settings" },
    ]},
  ];

  return (
    <div className="platform-admin-root bg-background font-body-md text-on-surface flex h-screen overflow-hidden">
      {/* SIDEBAR */}
      <aside className="flex flex-col h-screen bg-[#1e1b4b] fixed left-0 w-64 shadow-xl z-50 overflow-y-auto shrink-0">
        <div className="px-md pt-lg pb-sm">
          <div className="flex items-center gap-sm">
            <div className="w-7 h-7 bg-primary rounded-lg flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-white" style={{fontSize: '15px'}}>school</span>
            </div>
            <div>
              <p className="text-[13px] font-semibold text-white leading-tight">Telite LMS</p>
              <p className="text-[9px] font-medium text-white/60 uppercase tracking-widest mt-0.5">Global Admin Console</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-xs py-md space-y-md">
          {navGroups.map((group, idx) => (
            <div key={idx}>
              <p className="px-md mb-xs text-[9px] font-bold text-white/40 uppercase tracking-widest">{group.section}</p>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = item.exact ? pathname === item.id : pathname.startsWith(item.id);
                  return (
                    <Link
                      key={item.id}
                      to={item.id}
                      className={`flex items-center gap-[14px] px-[14px] py-[8px] rounded-lg cursor-pointer transition-all text-[11px] font-label-caps tracking-[0.08em] uppercase whitespace-nowrap ${
                        isActive 
                          ? 'bg-white/10 border border-white/20 text-white shadow-inner' 
                          : 'text-white/70 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      <span className="material-symbols-outlined" style={{fontSize: '17px'}}>{item.icon}</span>
                      {item.label}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-white/10 px-xs py-sm space-y-0.5">
          <Link to="/platform-admin/help" className="flex items-center gap-[14px] px-[14px] py-[8px] rounded-lg cursor-pointer transition-all text-[11px] font-label-caps tracking-[0.08em] uppercase whitespace-nowrap text-white/70 hover:text-white hover:bg-white/5">
            <span className="material-symbols-outlined" style={{fontSize: '17px'}}>help</span>Help
          </Link>
          <button onClick={onLogout} className="w-full flex items-center gap-[14px] px-[14px] py-[8px] rounded-lg cursor-pointer transition-all text-[11px] font-label-caps tracking-[0.08em] uppercase whitespace-nowrap text-white/70 hover:text-white hover:bg-white/5">
            <span className="material-symbols-outlined" style={{fontSize: '17px'}}>logout</span>Logout
          </button>
        </div>
      </aside>

      {/* MAIN */}
      <div className="flex-1 flex flex-col ml-64 h-screen overflow-hidden">
        {/* TOP NAV */}
        <header className="shrink-0 flex justify-between items-center px-container-padding py-sm sticky top-0 z-40 bg-white/60 backdrop-blur-xl border-b border-white/30 shadow-sm">
          <div className="flex items-center gap-lg">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline" style={{fontSize: '17px'}}>search</span>
              <input className="pl-10 pr-md py-xs bg-surface-container-low border-none rounded-full w-56 focus:outline-none focus:ring-2 focus:ring-primary/30 text-sm inset-input" placeholder="Global search..." type="text" />
            </div>
            <nav className="hidden md:flex items-center gap-lg">
               <Link to="/platform-admin" className={`text-sm ${pathname === '/platform-admin' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'}`}>Overview</Link>
               <Link to="/platform-admin/organizations" className={`text-sm ${pathname.includes('organizations') ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'}`}>Organizations</Link>
               <Link to="/platform-admin/admins" className={`text-sm ${pathname.includes('admins') ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'}`}>Admin Control</Link>
            </nav>
          </div>
          <div className="flex items-center gap-md">
            <button className="p-xs hover:bg-black/5 rounded-full relative">
              <span className="material-symbols-outlined text-on-surface" style={{fontSize: '21px'}}>notifications</span>
              <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full border-2 border-white"></span>
            </button>
            <button className="p-xs hover:bg-black/5 rounded-full">
              <span className="material-symbols-outlined text-on-surface" style={{fontSize: '21px'}}>apps</span>
            </button>
            <div className="flex items-center gap-sm pl-sm border-l border-outline-variant/40">
              <div className="text-right hidden sm:block">
                <p className="font-bold text-[13px] leading-none text-on-surface">{session?.user?.name || "Alex Rivera"}</p>
                <p className="text-outline text-[11px] mt-0.5">Platform Admin</p>
              </div>
              <div className="w-9 h-9 rounded-full bg-primary-container flex items-center justify-center text-white font-bold text-sm">{session?.user?.name?.[0] || "A"}</div>
            </div>
          </div>
        </header>

        {/* PAGES WRAPPER */}
        <div className="flex-1 relative overflow-y-auto" id="pwrap">
          {/* Background blobs */}
          <div className="fixed pointer-events-none" style={{top: '-10%', right: '-5%', width: '40%', height: '40%', background: 'rgba(70,72,212,0.05)', borderRadius: '50%', filter: 'blur(120px)', zIndex: 0}}></div>
          <div className="fixed pointer-events-none" style={{bottom: '-10%', left: '-5%', width: '30%', height: '30%', background: 'rgba(91,89,140,0.08)', borderRadius: '50%', filter: 'blur(100px)', zIndex: 0}}></div>

          <div className="relative z-10 p-container-padding pb-xl max-w-[1400px] mx-auto w-full">
            <Routes>
              <Route index element={<OverviewTab />} />
              <Route path="organizations" element={<OrganizationsTab />} />
              <Route path="admins" element={<AdminControlTab />} />
              <Route path="analytics" element={<AnalyticsTab />} />
              <Route path="moodle" element={<MoodleSyncTab />} />
              <Route path="audit" element={<AuditTab />} />
              <Route path="features" element={<FeatureFlagsTab />} />
              <Route path="settings" element={<SettingsTab />} />
              <Route path="help" element={<HelpTab />} />
            </Routes>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- OVERVIEW TAB ---
function OverviewTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    platformApi.getAnalyticsOverview()
      .then(res => setData(res.data))
      .catch(() => showToast("Failed to load overview", "error"))
      .finally(() => setLoading(false));
  }, [showToast]);

  if (loading) return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></div>;
  if (!data) return <div>Failed to load data</div>;

  const orgUsage = Array.isArray(data.org_usage) ? data.org_usage : [];
  const recentActivity = Array.isArray(data.recent_activity) ? data.recent_activity : [];

  return (
    <div className="space-y-lg animate-in fade-in duration-300">
      {/* Hero */}
      <div className="flex justify-between items-end">
        <div>
          <h2 className="font-h2 text-h2 text-on-surface">Platform Overview</h2>
          <p className="text-body-md text-on-surface-variant/80 mt-1">Global control center for all organizations</p>
        </div>
        <div className="flex items-center gap-sm glass-panel px-md py-xs rounded-full shadow-sm">
          <span className="material-symbols-outlined text-primary" style={{fontSize: '15px'}}>calendar_today</span>
          <span className="font-data-mono text-data-mono text-on-surface">October 24, 2023</span>
        </div>
      </div>

      {/* System Pulse */}
      <div className="glass-panel neumorphic-card rounded-xl px-lg py-sm flex flex-wrap items-center justify-between gap-md">
        <div className="flex items-center gap-md">
          <div className="flex items-center gap-xs bg-green-500/10 px-sm py-1 rounded-full">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            <span className="font-label-caps text-[11px] text-green-700 uppercase tracking-wider">All Systems Operational</span>
          </div>
          <div className="h-4 w-px bg-outline-variant/30"></div>
          <div className="flex items-center gap-xs">
            <span className="material-symbols-outlined text-primary" style={{fontSize: '16px'}}>hub</span>
            <span className="text-sm text-on-surface-variant">Moodle Gateway: <span className="text-primary font-semibold">API Connected · 142ms</span></span>
          </div>
        </div>
        <div className="flex items-center gap-lg">
          <span className="text-sm text-on-surface-variant"><span className="font-bold">2.4k</span> Active Sessions</span>
          <span className="font-data-mono text-[11px] text-outline">Last check: 1m ago</span>
        </div>
      </div>

      {/* 5 Metric Cards */}
      <div className="grid grid-cols-5 gap-grid-gutter">
        <div className="glass-panel neumorphic-card tilt-card rounded-xl p-md flex flex-col items-center text-center cursor-default">
          <span className="material-symbols-outlined text-primary mb-sm" style={{fontSize: '30px'}}>corporate_fare</span>
          <span className="font-data-mono text-data-mono text-outline mb-xs">Total Orgs</span>
          <span className="font-h2 text-h2 text-on-surface">{data.total_orgs || '1,284'}</span>
          <div className="mt-sm px-xs py-0.5 bg-primary/10 text-primary text-[10px] rounded-full font-bold">+12.5%</div>
        </div>
        <div className="glass-panel neumorphic-card tilt-card rounded-xl p-md flex flex-col items-center text-center cursor-default">
          <span className="material-symbols-outlined text-primary mb-sm" style={{fontSize: '30px'}}>account_balance</span>
          <span className="font-data-mono text-data-mono text-outline mb-xs">Colleges</span>
          <span className="font-h2 text-h2 text-on-surface">{data.total_colleges || '432'}</span>
          <div className="mt-sm px-xs py-0.5 bg-primary/10 text-primary text-[10px] rounded-full font-bold">+4.2%</div>
        </div>
        <div className="glass-panel neumorphic-card tilt-card rounded-xl p-md flex flex-col items-center text-center cursor-default">
          <span className="material-symbols-outlined text-primary mb-sm" style={{fontSize: '30px'}}>business_center</span>
          <span className="font-data-mono text-data-mono text-outline mb-xs">Companies</span>
          <span className="font-h2 text-h2 text-on-surface">{data.total_companies || '852'}</span>
          <div className="mt-sm px-xs py-0.5 bg-primary/10 text-primary text-[10px] rounded-full font-bold">+8.1%</div>
        </div>
        <div className="glass-panel neumorphic-card tilt-card rounded-xl p-md flex flex-col items-center text-center cursor-default">
          <span className="material-symbols-outlined text-primary mb-sm" style={{fontSize: '30px'}}>groups</span>
          <span className="font-data-mono text-data-mono text-outline mb-xs">Total Users</span>
          <span className="font-h2 text-h2 text-on-surface">{data.total_users || '2.4M'}</span>
          <div className="mt-sm px-xs py-0.5 bg-primary/10 text-primary text-[10px] rounded-full font-bold">+24%</div>
        </div>
        <div className="glass-panel neumorphic-card tilt-card rounded-xl p-md flex flex-col items-center text-center cursor-default">
          <span className="material-symbols-outlined text-primary mb-sm" style={{fontSize: '30px'}}>admin_panel_settings</span>
          <span className="font-data-mono text-data-mono text-outline mb-xs">Super Admins</span>
          <span className="font-h2 text-h2 text-on-surface">{data.total_super_admins || '156'}</span>
          <div className="mt-sm px-xs py-0.5 bg-surface-container text-outline text-[10px] rounded-full font-bold">Stable</div>
        </div>
      </div>

      {/* Table + Activity */}
      <div className="grid grid-cols-3 gap-grid-gutter">
        {/* Org Table */}
        <div className="col-span-2 glass-panel rounded-xl overflow-hidden shadow-sm">
          <div className="p-md flex justify-between items-center border-b border-white/20">
            <h3 className="font-h3 text-h3">Recent Organizations</h3>
            <Link to="/platform-admin/organizations" className="text-primary font-bold text-sm hover:underline">View All</Link>
          </div>
          <table className="w-full text-left">
            <thead className="bg-surface-container-low">
              <tr>
                <th className="px-md py-sm font-label-caps text-label-caps text-outline">Organization</th>
                <th className="px-md py-sm font-label-caps text-label-caps text-outline">Type</th>
                <th className="px-md py-sm font-label-caps text-label-caps text-outline">Users</th>
                <th className="px-md py-sm font-label-caps text-label-caps text-outline">Status</th>
                <th className="px-md py-sm font-label-caps text-label-caps text-outline">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/20">
              <tr className="hover:bg-white/30 transition-colors">
                <td className="px-md py-md"><div className="flex items-center gap-sm"><div className="w-8 h-8 rounded bg-primary-container flex items-center justify-center text-white font-bold text-xs">SU</div><span className="font-bold text-sm">Stanford University</span></div></td>
                <td className="px-md py-md text-sm text-on-surface-variant">College</td>
                <td className="px-md py-md font-data-mono text-sm">45,200</td>
                <td className="px-md py-md"><span className="inline-flex items-center gap-[3px] px-[10px] py-[2px] rounded-full font-bold text-[11px] uppercase tracking-wide bg-[#dcfce7] text-[#15803d]">Active</span></td>
                <td className="px-md py-md"><span className="material-symbols-outlined text-outline hover:text-primary cursor-pointer" style={{fontSize: '20px'}}>more_vert</span></td>
              </tr>
              <tr className="hover:bg-white/30 transition-colors">
                <td className="px-md py-md"><div className="flex items-center gap-sm"><div className="w-8 h-8 rounded bg-secondary-container flex items-center justify-center text-on-secondary-container font-bold text-xs">TS</div><span className="font-bold text-sm">Tesla Inc.</span></div></td>
                <td className="px-md py-md text-sm text-on-surface-variant">Company</td>
                <td className="px-md py-md font-data-mono text-sm">12,800</td>
                <td className="px-md py-md"><span className="inline-flex items-center gap-[3px] px-[10px] py-[2px] rounded-full font-bold text-[11px] uppercase tracking-wide bg-[#dcfce7] text-[#15803d]">Active</span></td>
                <td className="px-md py-md"><span className="material-symbols-outlined text-outline hover:text-primary cursor-pointer" style={{fontSize: '20px'}}>more_vert</span></td>
              </tr>
              <tr className="hover:bg-white/30 transition-colors">
                <td className="px-md py-md"><div className="flex items-center gap-sm"><div className="w-8 h-8 rounded bg-tertiary-container flex items-center justify-center text-white font-bold text-xs">OX</div><span className="font-bold text-sm">Oxford Academy</span></div></td>
                <td className="px-md py-md text-sm text-on-surface-variant">College</td>
                <td className="px-md py-md font-data-mono text-sm">8,400</td>
                <td className="px-md py-md"><span className="inline-flex items-center gap-[3px] px-[10px] py-[2px] rounded-full font-bold text-[11px] uppercase tracking-wide bg-[#fef3c7] text-[#92400e]">Syncing</span></td>
                <td className="px-md py-md"><span className="material-symbols-outlined text-outline hover:text-primary cursor-pointer" style={{fontSize: '20px'}}>more_vert</span></td>
              </tr>
              <tr className="hover:bg-white/30 transition-colors">
                <td className="px-md py-md"><div className="flex items-center gap-sm"><div className="w-8 h-8 rounded bg-primary flex items-center justify-center text-white font-bold text-xs">NT</div><span className="font-bold text-sm">Netflix Talent</span></div></td>
                <td className="px-md py-md text-sm text-on-surface-variant">Company</td>
                <td className="px-md py-md font-data-mono text-sm">4,150</td>
                <td className="px-md py-md"><span className="inline-flex items-center gap-[3px] px-[10px] py-[2px] rounded-full font-bold text-[11px] uppercase tracking-wide bg-[#dcfce7] text-[#15803d]">Active</span></td>
                <td className="px-md py-md"><span className="material-symbols-outlined text-outline hover:text-primary cursor-pointer" style={{fontSize: '20px'}}>more_vert</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Live Activity */}
        <div className="glass-panel rounded-xl overflow-hidden shadow-sm">
          <div className="p-md border-b border-white/20 flex items-center justify-between">
            <h3 className="font-h3 text-h3">Live Activity</h3>
            <span className="flex items-center gap-xs"><span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span><span className="font-label-caps text-[10px] text-outline uppercase">Live</span></span>
          </div>
          <div className="p-md space-y-md">
            <div className="flex gap-md"><div className="flex flex-col items-center"><div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary"><span className="material-symbols-outlined" style={{fontSize: '16px'}}>person_add</span></div><div className="w-0.5 h-6 bg-outline-variant/30 mt-1"></div></div><div className="pb-md"><p className="font-bold text-sm">New User Registered</p><p className="text-on-surface-variant text-xs">John Doe joined <span className="text-primary font-medium">Stanford University</span></p><p className="font-data-mono text-[11px] text-outline mt-1">2 minutes ago</p></div></div>
            <div className="flex gap-md"><div className="flex flex-col items-center"><div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-600"><span className="material-symbols-outlined" style={{fontSize: '16px'}}>sync</span></div><div className="w-0.5 h-6 bg-outline-variant/30 mt-1"></div></div><div className="pb-md"><p className="font-bold text-sm">Moodle Sync Started</p><p className="text-on-surface-variant text-xs">Auto-sync for <span className="text-primary font-medium">Oxford Academy</span></p><p className="font-data-mono text-[11px] text-outline mt-1">15 minutes ago</p></div></div>
            <div className="flex gap-md"><div className="w-8 h-8 rounded-full bg-error-container flex items-center justify-center text-error shrink-0"><span className="material-symbols-outlined" style={{fontSize: '16px'}}>lock</span></div><div><p className="font-bold text-sm">Security Alert</p><p className="text-on-surface-variant text-xs">Failed login on <span className="text-primary font-medium">Admin Console</span></p><p className="font-data-mono text-[11px] text-outline mt-1">45 minutes ago</p></div></div>
          </div>
        </div>
      </div>

      {/* Moodle Sync Strip */}
      <div className="glass-panel neumorphic-card p-md rounded-xl flex items-center justify-between border-l-4 border-primary">
        <div className="flex items-center gap-md">
          <div className="w-12 h-12 rounded-lg bg-[#f98012] flex items-center justify-center"><span className="material-symbols-outlined text-white" style={{fontSize: '24px'}}>sync_alt</span></div>
          <div><h4 className="font-bold text-body-lg">Moodle Global Sync Status</h4><p className="text-sm text-on-surface-variant">Last complete sync: Today, 04:30 AM (99.8% Success Rate)</p></div>
        </div>
        <div className="flex items-center gap-xl">
          <div className="flex flex-col items-end"><span className="font-data-mono text-data-mono text-primary">Next Sync: 12:00 PM</span><div className="w-44 h-[6px] bg-[#e5eeff] rounded-full overflow-hidden mt-xs"><div className="h-full rounded-full bg-primary" style={{width: '75%', boxShadow: '0 0 8px rgba(70,72,212,0.45)'}}></div></div></div>
          <button className="bg-white border border-outline-variant px-md py-sm rounded-lg font-bold hover:bg-surface-container-low transition-all text-sm">Sync Now</button>
        </div>
      </div>
      
      {/* Floating Action Button */}
      <button className="fixed bottom-lg right-lg w-14 h-14 bg-primary rounded-full shadow-2xl flex items-center justify-center hover-lift hover:scale-110 active:scale-95 transition-transform z-50">
        <span className="material-symbols-outlined text-white" style={{fontSize: '28px'}}>add</span>
      </button>
    </div>
  );
}

// --- ORGANIZATIONS TAB ---
function OrganizationsTab() {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();
  const [createOpen, setCreateOpen] = useState(false);

  const loadOrgs = () => {
    setLoading(true);
    platformApi.listOrganizations({ limit: 100 })
      .then(res => setOrgs(res.data.orgs))
      .catch(() => showToast("Failed to load organizations", "error"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadOrgs(); }, [showToast]);

  const handleToggleStatus = (org) => {
    const newStatus = org.status === "active" ? "suspended" : "active";
    platformApi.updateOrgStatus(org.id, newStatus)
      .then(() => { showToast(`Organization ${newStatus}`); loadOrgs(); })
      .catch(err => showToast(err.response?.data?.detail || "Failed to update status", "error"));
  };

  return (
    <div className="space-y-lg animate-in fade-in duration-300">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="font-h1 text-h1 text-on-surface">Organizations</h1>
          <p className="text-on-surface-variant text-body-lg mt-sm">Manage educational institutions and corporate partners.</p>
        </div>
        <button 
          className="bg-primary text-white px-xl py-md rounded-xl font-bold flex items-center gap-sm shadow-lg hover:shadow-primary/30 transition-all active:scale-95"
          onClick={() => setCreateOpen(true)}
        >
          <span className="material-symbols-outlined">add</span>New Organization
        </button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-md">
        <div className="glass-panel p-1 rounded-xl flex gap-1">
          <button className="px-lg py-2 bg-white text-primary font-bold rounded-lg shadow-sm text-sm">All</button>
          <button className="px-lg py-2 text-on-surface-variant hover:text-primary text-sm">Colleges</button>
          <button className="px-lg py-2 text-on-surface-variant hover:text-primary text-sm">Companies</button>
          <button className="px-lg py-2 text-on-surface-variant hover:text-primary text-sm">Inactive</button>
        </div>
        <div className="flex gap-sm">
          <button className="neumorphic-card bg-white px-md py-2 rounded-lg flex items-center gap-xs text-on-surface-variant hover:text-primary text-sm">
            <span className="material-symbols-outlined" style={{fontSize: '17px'}}>filter_list</span>Filter
          </button>
          <button className="neumorphic-card bg-white px-md py-2 rounded-lg flex items-center gap-xs text-on-surface-variant hover:text-primary text-sm">
            <span className="material-symbols-outlined" style={{fontSize: '17px'}}>download</span>Export CSV
          </button>
        </div>
      </div>

      <div className="grid px-xl font-label-caps text-label-caps text-outline uppercase tracking-widest gap-md" style={{gridTemplateColumns: '2fr 1fr 1.1fr 1.3fr .8fr .5fr'}}>
        <div>Organization</div><div>Type</div><div>Domain</div><div>Super Admin</div><div>Status</div><div className="text-right">Actions</div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        orgs.map(o => (
          <div key={o.id} className="hover-lift glass-panel rounded-2xl p-md px-xl grid items-center gap-md mb-md" style={{gridTemplateColumns: '2fr 1fr 1.1fr 1.3fr .8fr .5fr'}}>
            <div className="flex items-center gap-md">
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${o.type === 'college' ? 'bg-primary/10' : 'bg-tertiary-fixed-dim'}`}>
                <span className={`material-symbols-outlined ${o.type === 'college' ? 'text-primary' : 'text-tertiary'}`} style={{fontSize: '26px'}}>{o.type === 'college' ? 'account_balance' : 'business'}</span>
              </div>
              <div>
                <p className="font-bold text-sm">{o.name}</p>
                <p className="text-outline text-xs">ID: {o.id}</p>
              </div>
            </div>
            <div>
              <span className={`px-sm py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${o.type === 'college' ? 'bg-primary-container/10 text-primary' : 'bg-secondary-container/20 text-secondary'}`}>
                {o.type}
              </span>
            </div>
            <div>
              <span className="font-data-mono text-data-mono text-primary text-xs">{o.domain}</span>
            </div>
            <div className="flex items-center gap-sm">
              <div className="w-7 h-7 rounded-full bg-indigo-200 flex items-center justify-center text-xs font-bold text-indigo-800">AD</div>
              <span className="text-sm">Admin Users ({o.user_count})</span>
            </div>
            <div className={`flex items-center gap-xs ${o.status === 'active' ? 'text-green-600' : 'text-error'}`}>
              <span className={`w-2 h-2 rounded-full ${o.status === 'active' ? 'bg-green-500' : 'bg-error'}`}></span>
              <span className="font-bold text-xs">{o.status === 'active' ? 'Active' : 'Suspended'}</span>
            </div>
            <div className="flex justify-end gap-1">
              <button 
                className="w-8 h-8 rounded-lg hover:bg-primary/10 text-primary flex items-center justify-center"
                title="View"
              >
                <span className="material-symbols-outlined" style={{fontSize: '17px'}}>visibility</span>
              </button>
              <button 
                className="w-8 h-8 rounded-lg hover:bg-secondary/10 text-secondary flex items-center justify-center"
                title={o.status === 'active' ? 'Suspend' : 'Activate'}
                onClick={() => handleToggleStatus(o)}
              >
                <span className="material-symbols-outlined" style={{fontSize: '17px'}}>{o.status === 'active' ? 'block' : 'check_circle'}</span>
              </button>
            </div>
          </div>
        ))
      )}
      {!loading && orgs.length === 0 && <div className="text-center p-xl text-outline">No organizations found.</div>}

      <div className="flex items-center justify-between py-md">
        <p className="text-outline-variant text-sm">Showing {orgs.length} organizations</p>
        <div className="flex items-center gap-sm">
          <button className="neumorphic-card w-10 h-10 rounded-lg flex items-center justify-center text-outline bg-white"><span className="material-symbols-outlined">chevron_left</span></button>
          <button className="w-10 h-10 rounded-lg bg-primary text-white font-bold">1</button>
          <button className="neumorphic-card w-10 h-10 rounded-lg flex items-center justify-center text-outline bg-white"><span className="material-symbols-outlined">chevron_right</span></button>
        </div>
      </div>

      {createOpen && <CreateOrganizationModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={() => { setCreateOpen(false); loadOrgs(); }} />}
    </div>
  );
}

// --- ADMIN CONTROL TAB ---
function AdminControlTab() {
  const [data, setData] = useState({ admins: [], pending_invitations: [] });
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();
  const [inviteOpen, setInviteOpen] = useState(false);

  const loadAdmins = () => {
    setLoading(true);
    platformApi.listAdmins()
      .then(res => setData(res.data))
      .catch(() => showToast("Failed to load admins", "error"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadAdmins(); }, [showToast]);

  const handleToggleAdminStatus = (admin) => {
    const nextStatus = admin.status === "active" ? "suspended" : "active";
    platformApi.updateAdminStatus(admin.id, nextStatus)
      .then(() => { showToast(`Admin ${nextStatus}`); loadAdmins(); })
      .catch(err => showToast(err.response?.data?.detail || "Failed to update admin status", "error"));
  };

  return (
    <div className="space-y-xl animate-in fade-in duration-300">
      <div>
        <h2 className="font-h1 text-h1 text-on-surface mb-xs">Admin Control</h2>
        <p className="font-body-lg text-on-surface-variant">Manage organization-level access and system-wide configurations.</p>
      </div>

      <div className="grid grid-cols-4 gap-grid-gutter">
        <div className="neumorphic-card bg-surface rounded-xl p-md border border-white/40">
          <div className="flex justify-between items-start mb-sm">
            <span className="material-symbols-outlined text-primary p-xs bg-primary/10 rounded-lg" style={{fontSize: '20px'}}>shield_person</span>
            <span className="text-on-surface-variant font-data-mono text-xs">+12%</span>
          </div>
          <div className="font-h3 text-h3 font-bold">{data.admins.filter(a => a.role === 'super_admin').length}</div>
          <div className="font-label-caps text-label-caps text-on-surface-variant mt-1">Total Super Admins</div>
        </div>
        <div className="neumorphic-card bg-surface rounded-xl p-md border border-white/40">
          <div className="flex justify-between items-start mb-sm">
            <span className="material-symbols-outlined text-green-600 p-xs bg-green-100 rounded-lg" style={{fontSize: '20px'}}>fiber_manual_record</span>
            <span className="text-on-surface-variant font-data-mono text-xs">+4 today</span>
          </div>
          <div className="font-h3 text-h3 font-bold">{data.admins.filter(a => a.status === 'active').length}</div>
          <div className="font-label-caps text-label-caps text-on-surface-variant mt-1">Active Admins</div>
        </div>
        <div className="neumorphic-card bg-surface rounded-xl p-md border border-white/40">
          <div className="flex justify-between items-start mb-sm">
            <span className="material-symbols-outlined text-error p-xs bg-error-container/30 rounded-lg" style={{fontSize: '20px'}}>block</span>
            <span className="text-on-surface-variant font-data-mono text-xs">-2%</span>
          </div>
          <div className="font-h3 text-h3 font-bold">{data.admins.filter(a => a.status === 'suspended').length}</div>
          <div className="font-label-caps text-label-caps text-on-surface-variant mt-1">Suspended Accounts</div>
        </div>
        <div className="neumorphic-card bg-surface rounded-xl p-md border border-white/40">
          <div className="flex justify-between items-start mb-sm">
            <span className="material-symbols-outlined text-secondary p-xs bg-secondary-container/30 rounded-lg" style={{fontSize: '20px'}}>hourglass_empty</span>
            <span className="text-on-surface-variant font-data-mono text-xs">Waiting</span>
          </div>
          <div className="font-h3 text-h3 font-bold">{data.pending_invitations.length}</div>
          <div className="font-label-caps text-label-caps text-on-surface-variant mt-1">Pending Invites</div>
        </div>
      </div>

      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="flex items-center border-b border-white/20 px-md">
          <button className="px-md py-md font-label-caps text-label-caps text-primary border-b-2 border-primary tracking-wider">Super Admins</button>
          <button className="px-md py-md font-label-caps text-label-caps text-on-surface-variant hover:text-primary tracking-wider">All Org Admins</button>
          <button className="px-md py-md font-label-caps text-label-caps text-on-surface-variant hover:text-primary tracking-wider">Pending Invitations</button>
          <div className="ml-auto flex items-center gap-sm">
            <button className="p-xs hover:bg-white/20 rounded-lg" onClick={() => setInviteOpen(true)} title="Send Invite"><span className="material-symbols-outlined text-on-surface-variant">person_add</span></button>
            <button className="p-xs hover:bg-white/20 rounded-lg"><span className="material-symbols-outlined text-on-surface-variant">filter_list</span></button>
            <button className="p-xs hover:bg-white/20 rounded-lg"><span className="material-symbols-outlined text-on-surface-variant">download</span></button>
          </div>
        </div>
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-low/50">
              <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">Name</th>
              <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">Organization</th>
              <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">Role</th>
              <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">Last Login</th>
              <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">Status</th>
              <th className="px-md py-sm"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {loading ? <tr><td colSpan="6" className="p-8 text-center"><div className="inline-block w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></td></tr> : data.admins.map(a => (
              <tr key={a.id} className="group hover:bg-white/10 transition-colors">
                <td className="px-md py-md">
                  <div className="flex items-center gap-sm">
                    <div className="w-9 h-9 rounded-full bg-primary-fixed-dim flex items-center justify-center font-bold text-primary text-sm">
                      {a.full_name?.substring(0, 2).toUpperCase() || 'AD'}
                    </div>
                    <div>
                      <div className="font-semibold text-sm">{a.full_name}</div>
                      <div className="text-xs text-on-surface-variant">{a.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-md py-md">
                  <div className="text-sm">{a.org_name || 'Platform'}</div>
                  <span className="font-label-caps text-[10px] text-secondary bg-secondary-container/20 px-2 py-0.5 rounded-full">Enterprise</span>
                </td>
                <td className="px-md py-md">
                  <span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-xs font-semibold">{a.role.replace('_', ' ')}</span>
                </td>
                <td className="px-md py-md font-data-mono text-xs text-on-surface-variant">2024-05-21 09:12</td>
                <td className="px-md py-md">
                  <div className={`flex items-center gap-xs ${a.status === 'active' ? 'text-green-600' : 'text-error'}`}>
                    <div className={`w-2 h-2 rounded-full ${a.status === 'active' ? 'bg-green-500' : 'bg-error'}`}></div>
                    <span className="text-sm font-medium">{a.status === 'active' ? 'Active' : 'Suspended'}</span>
                  </div>
                </td>
                <td className="px-md py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="flex gap-xs justify-end">
                    <button className="p-xs text-on-surface-variant hover:text-primary hover:bg-white/30 rounded-lg">
                      <span className="material-symbols-outlined text-sm">vpn_key</span>
                    </button>
                    <button 
                      onClick={() => handleToggleAdminStatus(a)}
                      className="p-xs text-on-surface-variant hover:text-error hover:bg-error-container/20 rounded-lg"
                    >
                      <span className="material-symbols-outlined text-sm">{a.status === 'active' ? 'block' : 'settings_backup_restore'}</span>
                    </button>
                    <button className="p-xs text-on-surface-variant hover:text-error hover:bg-error-container/20 rounded-lg">
                      <span className="material-symbols-outlined text-sm">delete</span>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-md py-sm bg-surface-container-low/30 border-t border-white/20 flex items-center justify-between">
          <span className="text-sm text-on-surface-variant">Showing {data.admins.length} administrators</span>
          <div className="flex gap-xs">
            <button className="p-xs border border-white/40 rounded-lg opacity-50" disabled><span className="material-symbols-outlined">chevron_left</span></button>
            <button className="p-xs border border-white/40 rounded-lg hover:bg-white/20"><span className="material-symbols-outlined">chevron_right</span></button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-grid-gutter pb-xl">
        <div className="glass-panel p-md rounded-xl space-y-sm">
          <div className="flex items-center gap-xs text-primary mb-xs">
            <span className="material-symbols-outlined" style={{fontVariationSettings: "'FILL' 1"}}>security</span>
            <h4 className="text-sm font-bold uppercase tracking-widest">Security Audit</h4>
          </div>
          <p className="text-sm text-on-surface-variant">Last sweep 4 hours ago. No unusual login attempts detected across the global admin network.</p>
          <button className="text-primary font-semibold text-sm hover:underline">View Detailed Log</button>
        </div>
        <div className="glass-panel p-md rounded-xl space-y-sm">
          <div className="flex items-center gap-xs text-secondary mb-xs">
            <span className="material-symbols-outlined" style={{fontVariationSettings: "'FILL' 1"}}>mail</span>
            <h4 className="text-sm font-bold uppercase tracking-widest">Invite Expiry</h4>
          </div>
          <p className="text-sm text-on-surface-variant">12 invitations expiring in the next 24 hours. Consider re-sending reminders to pending admins.</p>
          <button className="text-secondary font-semibold text-sm hover:underline">Remind All</button>
        </div>
        <div className="glass-panel p-md rounded-xl space-y-sm">
          <div className="flex items-center gap-xs mb-xs">
            <span className="material-symbols-outlined" style={{fontVariationSettings: "'FILL' 1"}}>history</span>
            <h4 className="text-sm font-bold uppercase tracking-widest">Recent Activity</h4>
          </div>
          <ul className="space-y-xs">
            <li className="flex items-start gap-xs text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1 shrink-0"></span>
              <span>Sarah Connor modified permissions for 'Org_Alpha'</span>
            </li>
            <li className="flex items-start gap-xs text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1 shrink-0"></span>
              <span>New invitation sent to david.v@tech.com</span>
            </li>
          </ul>
        </div>
      </div>

      {inviteOpen && <InviteAdminModal open={inviteOpen} onClose={() => setInviteOpen(false)} onInvited={() => { setInviteOpen(false); loadAdmins(); }} />}
    </div>
  );
}

// --- MOODLE SYNC TAB ---
function MoodleSyncTab() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();
  const [syncingOrgId, setSyncingOrgId] = useState(null);

  const loadTenants = () => {
    setLoading(true);
    platformApi.listMoodleTenants()
      .then(res => setTenants(res.data))
      .catch(() => showToast("Failed to load moodle tenants", "error"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadTenants(); }, [showToast]);

  const handleSyncAll = () => {
    platformApi.syncAllMoodle()
      .then(res => { showToast(`Triggered sync for ${res.data.triggered} orgs`); loadTenants(); })
      .catch(() => showToast("Failed to trigger sync", "error"));
  };

  const handleSyncOrg = async (orgId) => {
    setSyncingOrgId(orgId);
    try {
      await platformApi.syncOrgMoodle(orgId);
      showToast("Sync triggered");
      loadTenants();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to trigger sync", "error");
    } finally {
      setSyncingOrgId(null);
    }
  };

  return (
    <div className="space-y-lg animate-in fade-in duration-300">
      <div className="glass-panel rounded-xl p-md flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-md">
          <div className="relative">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          </div>
          <div>
            <h2 className="font-h3 text-h3">Moodle LMS Gateway</h2>
            <p className="text-sm text-on-surface-variant">https://moodle.telite-edu.com/api/v2</p>
          </div>
        </div>
        <div className="flex gap-md items-center">
          <div className="px-md py-xs rounded-full bg-green-100 text-green-700 font-label-caps text-label-caps flex items-center gap-xs">
            <span className="material-symbols-outlined" style={{fontSize: '13px'}}>check_circle</span>CONNECTED
          </div>
          <div className="text-right">
            <p className="font-label-caps text-label-caps text-on-surface-variant">LATENCY</p>
            <p className="font-data-mono text-data-mono text-primary">24ms</p>
          </div>
          <button 
            className="neumorphic-card bg-primary text-white px-lg py-sm rounded-lg font-label-caps flex items-center gap-xs hover:scale-95 transition-transform"
            onClick={handleSyncAll}
          >
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>sync</span>Sync All
          </button>
        </div>
      </div>

      <div className="flex flex-col xl:flex-row gap-grid-gutter items-start">
        <div className="flex-1 w-full glass-panel rounded-xl overflow-hidden shadow-lg">
          <div className="p-md border-b border-white/20 bg-white/20 flex justify-between items-center">
            <h3 className="font-h3 text-h3">Tenant Mapping</h3>
            <div className="flex gap-xs">
              <button className="p-xs hover:bg-white/30 rounded-lg text-outline"><span className="material-symbols-outlined">filter_list</span></button>
              <button className="p-xs hover:bg-white/30 rounded-lg text-outline"><span className="material-symbols-outlined">more_vert</span></button>
            </div>
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left border-b border-white/10">
                <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">Moodle Category</th>
                <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">LMS Tenant</th>
                <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">Status</th>
                <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant">Last Sync</th>
                <th className="px-md py-sm font-label-caps text-label-caps text-on-surface-variant text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? <tr><td colSpan="5" className="p-8 text-center"><div className="inline-block w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></td></tr> : tenants.map(t => (
                <tr key={t.id} className={`hover:bg-white/20 cursor-pointer ${t.sync_status === 'synced' ? 'bg-primary/5 border-l-4 border-primary' : ''}`}>
                  <td className="px-md py-md">
                    <div className="flex items-center gap-sm">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${t.sync_status === 'synced' ? 'bg-indigo-100 text-primary' : 'bg-slate-100 text-slate-500'}`}>
                        <span className="material-symbols-outlined">category</span>
                      </div>
                      <div>
                        <p className="font-bold text-sm">CAT-{t.moodle_cat_id}</p>
                        <p className="text-[11px] text-on-surface-variant uppercase tracking-widest">{t.org_name}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-md py-md text-sm">{t.org_name}</td>
                  <td className="px-md py-md">
                    <div className={`flex items-center gap-xs ${t.sync_status === 'synced' ? 'text-green-600' : 'text-error'}`}>
                      <span className="material-symbols-outlined" style={{fontSize: '16px'}}>
                        {t.sync_status === 'synced' ? 'done_all' : 'error_outline'}
                      </span>
                      <span className="font-label-caps text-xs">{t.sync_status === 'synced' ? 'Successful' : 'Failed'}</span>
                    </div>
                  </td>
                  <td className="px-md py-md">
                    <p className="font-data-mono text-xs text-on-surface-variant">{t.last_sync_at ? new Date(t.last_sync_at).toLocaleString() : 'Never'}</p>
                  </td>
                  <td className="px-md py-md text-right">
                    <button 
                      disabled={syncingOrgId === t.org_id}
                      onClick={(e) => { e.stopPropagation(); handleSyncOrg(t.org_id); }}
                      className="neumorphic-card bg-white/80 p-xs rounded-lg text-primary hover:bg-white disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined">refresh</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="w-full xl:w-80 flex flex-col gap-md">
          <div className="glass-panel rounded-xl p-md shadow-lg">
            <div className="flex justify-between items-center mb-md">
              <h4 className="font-semibold text-[17px]">Sync Logs</h4>
              <span className="font-label-caps text-label-caps text-primary bg-primary/10 px-xs py-0.5 rounded text-xs">System</span>
            </div>
            <div className="space-y-md">
              <div className="relative pl-md border-l border-primary/40">
                <div className="absolute -left-[5px] top-0 w-2.5 h-2.5 rounded-full bg-primary"></div>
                <p className="font-label-caps text-[10px] text-on-surface-variant uppercase">14:02:11</p>
                <p className="text-[13px] text-on-surface leading-tight mt-1">Successfully synced 12 new course enrollments from Moodle.</p>
              </div>
              <div className="relative pl-md border-l border-slate-200">
                <div className="absolute -left-[5px] top-0 w-2.5 h-2.5 rounded-full bg-slate-300"></div>
                <p className="font-label-caps text-[10px] text-on-surface-variant uppercase">14:00:05</p>
                <p className="text-[13px] text-on-surface leading-tight mt-1">Handshake initiated with /webservice/rest/server.php</p>
              </div>
            </div>
            <button className="w-full mt-lg py-sm text-label-caps text-primary border border-primary/20 rounded-lg hover:bg-primary/5 transition-all text-xs font-bold tracking-widest">View Detailed Log</button>
          </div>
          <div className="glass-panel rounded-xl p-md shadow-lg relative overflow-hidden">
            <h4 className="font-label-caps text-label-caps text-on-surface-variant mb-xs">HEALTH METRIC</h4>
            <div className="flex items-end justify-between">
              <p className="font-h2 text-h2 text-primary">98.2<span className="text-body-md">%</span></p>
              <span className="material-symbols-outlined text-indigo-200" style={{fontSize: '44px'}}>analytics</span>
            </div>
            <p className="text-xs text-on-surface-variant mt-sm">Average sync success rate across all category tunnels over the last 30 days.</p>
            <div className="h-2 w-full bg-surface-container mt-md rounded-full overflow-hidden">
              <div className="h-full bg-primary rounded-full shadow-lg" style={{width: '98.2%'}}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- AUDIT TAB ---
function AuditTab() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});
  const { showToast } = useToast();

  useEffect(() => {
    platformApi.listAuditLogs({ limit: 50 })
      .then(res => setLogs(res.data.logs))
      .catch(() => showToast("Failed to load audit logs", "error"))
      .finally(() => setLoading(false));
  }, [showToast]);

  const toggleAudit = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="space-y-lg animate-in fade-in duration-300 relative z-10 pb-xl">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-md">
        <div>
          <h2 className="font-h2 text-[32px] mb-xs text-on-surface font-bold">System Audit Log</h2>
          <p className="text-sm text-on-surface-variant">Real-time mission control monitoring of all administrative actions and security events.</p>
        </div>
        <div className="flex gap-sm">
          <button className="neumorphic-card bg-white px-md py-sm rounded-xl flex items-center gap-xs font-label-caps text-[11px] text-primary hover:scale-105 transition-all shadow-sm">
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>download</span>Export CSV
          </button>
          <button className="bg-primary text-on-primary px-md py-sm rounded-xl flex items-center gap-xs font-label-caps text-[11px] shadow-lg shadow-primary/30">
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>refresh</span>Refresh Logs
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-panel rounded-2xl p-md neumorphic-card grid grid-cols-4 gap-md bg-white/40">
        <div className="space-y-xs">
          <label className="font-label-caps text-[11px] text-outline-variant">Date Range</label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline" style={{fontSize: '14px'}}>calendar_today</span>
            <select className="w-full pl-10 pr-sm py-xs bg-white border border-outline-variant rounded-lg text-sm appearance-none focus:outline-none inset-input">
              <option>Last 24 Hours</option><option>Last 7 Days</option>
            </select>
          </div>
        </div>
        <div className="space-y-xs">
          <label className="font-label-caps text-[11px] text-outline-variant">Organization</label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline" style={{fontSize: '14px'}}>corporate_fare</span>
            <select className="w-full pl-10 pr-sm py-xs bg-white border border-outline-variant rounded-lg text-sm appearance-none focus:outline-none inset-input">
              <option>All Organizations</option>
            </select>
          </div>
        </div>
        <div className="space-y-xs">
          <label className="font-label-caps text-[11px] text-outline-variant">Severity</label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline" style={{fontSize: '14px'}}>priority_high</span>
            <select className="w-full pl-10 pr-sm py-xs bg-white border border-outline-variant rounded-lg text-sm appearance-none focus:outline-none inset-input">
              <option>All Levels</option><option>Critical</option>
            </select>
          </div>
        </div>
        <div className="space-y-xs">
          <label className="font-label-caps text-[11px] text-outline-variant">Search Target</label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline" style={{fontSize: '14px'}}>fingerprint</span>
            <input className="w-full pl-10 pr-sm py-xs bg-white border border-outline-variant rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary inset-input" placeholder="ID, Actor, or IP..." />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="glass-panel rounded-2xl overflow-hidden neumorphic-card bg-white/60">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-low border-b border-outline-variant/30">
              <th className="px-md py-sm font-label-caps text-[11px] text-on-surface-variant">Timestamp</th>
              <th className="px-md py-sm font-label-caps text-[11px] text-on-surface-variant">Action</th>
              <th className="px-md py-sm font-label-caps text-[11px] text-on-surface-variant">Actor</th>
              <th className="px-md py-sm font-label-caps text-[11px] text-on-surface-variant">Target</th>
              <th className="px-md py-sm font-label-caps text-[11px] text-on-surface-variant text-center">Status</th>
              <th className="px-md py-sm"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/20">
            {loading ? <tr><td colSpan="6" className="p-8 text-center"><div className="inline-block w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></td></tr> : logs.map(l => (
              <React.Fragment key={l.id}>
                <tr className="hover:bg-white/50 cursor-pointer group transition-colors" onClick={() => toggleAudit(l.id)}>
                  <td className="px-md py-md font-data-mono text-primary text-xs">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="px-md py-md">
                    <span className="bg-primary/10 text-primary px-sm py-1 rounded-full text-xs font-bold font-data-mono border border-primary/20">{l.action}</span>
                  </td>
                  <td className="px-md py-md">
                    <div className="flex items-center gap-sm">
                      <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-[10px] font-bold text-on-secondary-container">{(l.actor_name || 'SY')[0]}</div>
                      <div>
                        <p className="text-sm font-bold">{l.actor_name || 'System'}</p>
                        <p className="text-[10px] text-outline">User ID: {l.actor_id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-md py-md">
                    <p className="text-sm">{l.target_type}:{l.target_id}</p>
                    <p className="text-[10px] text-outline">{l.message}</p>
                  </td>
                  <td className="px-md py-md text-center">
                    <span className="material-symbols-outlined text-green-500">check_circle</span>
                  </td>
                  <td className="px-md py-md text-right">
                    <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
                      {expanded[l.id] ? 'expand_less' : 'expand_more'}
                    </span>
                  </td>
                </tr>
                {expanded[l.id] && (
                  <tr>
                    <td colSpan="6" className="p-0">
                      <div className="p-md bg-[#0f172a]">
                        <div className="flex justify-between items-center mb-sm px-sm">
                          <h4 className="font-label-caps text-[11px] text-primary-fixed-dim">Metadata Payload</h4>
                          <span className="text-[10px] font-data-mono text-outline-variant">TRACE-ID: {l.id}</span>
                        </div>
                        <div className="font-data-mono text-xs text-white/80 whitespace-pre p-sm bg-black/30 rounded-lg overflow-x-auto">
                          {JSON.stringify({ actor: l.actor_id, action: l.action, target: l.target_type, timestamp: l.created_at, metadata: l.metadata || {} }, null, 2)}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {!loading && logs.length === 0 && <tr><td colSpan="6" className="p-8 text-center text-outline">No logs found</td></tr>}
          </tbody>
        </table>
        <div className="bg-surface-container-low px-md py-sm flex justify-between items-center">
          <p className="font-label-caps text-[10px] text-outline-variant">Showing {logs.length ? 1 : 0}-{logs.length} of {logs.length} events</p>
          <div className="flex gap-xs">
            <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-outline-variant/30 text-outline hover:bg-white"><span className="material-symbols-outlined text-sm">chevron_left</span></button>
            <button className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary text-on-primary font-data-mono text-xs shadow-md">1</button>
            <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-outline-variant/30 text-outline hover:bg-white"><span className="material-symbols-outlined text-sm">chevron_right</span></button>
          </div>
        </div>
      </div>

      {/* Mission Control */}
      <div className="grid grid-cols-3 gap-lg pb-xl">
        <div className="glass-panel neumorphic-card p-md rounded-2xl border-l-4 border-error">
          <div className="flex items-center justify-between mb-sm">
            <span className="font-label-caps text-[11px] text-error">Security Alerts</span>
            <span className="bg-error/10 text-error px-xs py-0.5 rounded text-[10px] font-bold">CRITICAL</span>
          </div>
          <div className="flex items-center gap-md">
            <div className="text-[32px] font-bold text-on-surface">12</div>
            <div className="flex-1 h-2 bg-surface-container rounded-full overflow-hidden">
              <div style={{width:'65%',height:'100%',background:'#ba1a1a',borderRadius:'9999px',boxShadow:'0 0 8px rgba(186,26,26,0.45)'}}></div>
            </div>
          </div>
          <p className="text-xs text-outline-variant mt-sm">Suspicious login attempts in Tokyo region.</p>
        </div>
        <div className="glass-panel neumorphic-card p-md rounded-2xl border-l-4 border-primary">
          <div className="flex items-center justify-between mb-sm">
            <span className="font-label-caps text-[11px] text-primary">System Throughput</span>
            <span className="bg-primary/10 text-primary px-xs py-0.5 rounded text-[10px] font-bold">HEALTHY</span>
          </div>
          <div className="flex items-center gap-md">
            <div className="text-[32px] font-bold text-on-surface">4.2k</div>
            <div className="flex-1 h-2 bg-surface-container rounded-full overflow-hidden">
              <div style={{width:'82%',height:'100%',background:'#4648d4',borderRadius:'9999px'}}></div>
            </div>
          </div>
          <p className="text-xs text-outline-variant mt-sm">Admin ops per hour within normal baseline.</p>
        </div>
        <div className="glass-panel neumorphic-card p-md rounded-2xl border-l-4 border-secondary">
          <div className="flex items-center justify-between mb-sm">
            <span className="font-label-caps text-[11px] text-secondary">Active Sessions</span>
            <span className="bg-secondary/10 text-secondary px-xs py-0.5 rounded text-[10px] font-bold">STABLE</span>
          </div>
          <div className="flex items-center gap-md">
            <div className="text-[32px] font-bold text-on-surface">84</div>
            <div className="flex-1 h-2 bg-surface-container rounded-full overflow-hidden">
              <div style={{width:'45%',height:'100%',background:'#5b598c',borderRadius:'9999px',boxShadow:'0 0 8px rgba(91,89,140,0.45)'}}></div>
            </div>
          </div>
          <p className="text-xs text-outline-variant mt-sm">Authorized admin sessions currently live.</p>
        </div>
      </div>
    </div>
  );
}

// --- FEATURE FLAGS TAB ---
function FeatureFlagsTab() {
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    platformApi.listFeatureFlags()
      .then(res => setFlags(res.data))
      .catch(() => showToast("Failed to load feature flags", "error"))
      .finally(() => setLoading(false));
  }, [showToast]);

  const handleToggle = (orgId, featureKey, currentVal) => {
    platformApi.toggleFeatureFlag(orgId, featureKey, !currentVal)
      .then(res => {
        setFlags(prev => prev.map(f => f.org_id === orgId ? { ...f, flags: res.data.flags } : f));
        showToast(`Feature updated`, "success");
      })
      .catch(() => showToast("Failed to update flag", "error"));
  };

  const featureKeys = flags.length > 0 ? Object.keys(flags[0].flags) : [];

  const icons = {
    "moodle_access": "integration_instructions",
    "pal_tracking": "track_changes",
    "analytics": "analytics",
    "cloud_modules": "cloud_done"
  };

  const getIcon = (key) => icons[key] || "toggle_on";

  return (
    <div className="p-container-padding space-y-lg pb-xl relative z-10 animate-in fade-in duration-300">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="font-h1 text-[32px] font-bold text-on-surface">Feature Flags Matrix</h2>
          <p className="font-body-lg text-on-surface-variant mt-xs">Manage system capabilities across your client ecosystem.</p>
        </div>
        <div className="flex gap-sm">
          <button className="neumorphic-card bg-white px-md py-sm rounded-xl flex items-center gap-xs font-bold text-primary text-sm shadow-sm">
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>download</span>Export Report
          </button>
          <button className="bg-primary text-on-primary px-md py-sm rounded-xl font-bold flex items-center gap-xs shadow-lg hover:bg-primary-container text-sm transition-colors">
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>refresh</span>Re-sync All
          </button>
        </div>
      </div>

      <div className="glass-panel rounded-2xl overflow-hidden shadow-sm bg-white/60 border border-white/40">
        <div className="grid bg-white/70 backdrop-blur border-b border-white/40 sticky top-0 z-10" style={{gridTemplateColumns: `260px repeat(${Math.max(featureKeys.length, 1)}, 1fr)`}}>
          <div className="p-md font-label-caps text-[11px] text-outline uppercase tracking-widest flex items-center">Organization</div>
          {featureKeys.length > 0 ? featureKeys.map(k => (
            <div key={k} className="p-md text-center">
              <div className="flex flex-col items-center gap-1">
                <span className="material-symbols-outlined text-primary" style={{fontSize: '18px'}}>{getIcon(k)}</span>
                <span className="font-label-caps text-[10px] text-outline uppercase tracking-widest">{k.replace('_', ' ')}</span>
              </div>
            </div>
          )) : (
            <div className="p-md text-center text-outline text-xs">No feature flags configured</div>
          )}
        </div>
        <div className="divide-y divide-white/40">
          {loading ? (
            <div className="p-8 text-center"><div className="inline-block w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></div>
          ) : flags.map(f => (
            <div key={f.org_id} className="grid hover:bg-white/50 transition-colors" style={{gridTemplateColumns: `260px repeat(${Math.max(featureKeys.length, 1)}, 1fr)`}}>
              <div className="p-md flex items-center gap-md">
                <div className="w-10 h-10 rounded-xl bg-surface-container-highest flex items-center justify-center text-primary">
                  <span className="material-symbols-outlined">apartment</span>
                </div>
                <div>
                  <p className="font-semibold text-sm">{f.org_name}</p>
                  <span className="font-label-caps text-[10px] text-outline-variant">TENANT</span>
                </div>
              </div>
              {featureKeys.map(k => (
                <div key={k} className="p-md flex justify-center items-center">
                  <div 
                    className={`tog ${f.flags[k] ? 'on' : ''} cursor-pointer`} 
                    onClick={() => handleToggle(f.org_id, k, f.flags[k])}
                  ></div>
                </div>
              ))}
            </div>
          ))}
          {!loading && flags.length === 0 && <div className="p-8 text-center text-outline">No feature flags found</div>}
        </div>
      </div>

      {/* Legend */}
      <div className="glass-panel p-lg rounded-2xl bg-white/40 border border-white/40 mt-lg">
        <div className="flex items-center gap-sm mb-md">
          <span className="material-symbols-outlined text-primary">info</span>
          <h3 className="font-h3 text-h3 text-on-surface">Configuration Legend</h3>
        </div>
        <div className="grid grid-cols-3 gap-lg">
          <div className="flex items-start gap-md">
            <div className="w-3 h-12 bg-primary rounded-full mt-1 shrink-0 shadow-[0_0_8px_rgba(70,72,212,0.4)]"></div>
            <div>
              <p className="font-bold text-sm text-on-surface">Active State (ON)</p>
              <p className="text-on-surface-variant mt-1 text-sm">Enables the feature key immediately for all users. Syncs with cloud storage in &lt;200ms.</p>
            </div>
          </div>
          <div className="flex items-start gap-md">
            <div className="w-3 h-12 bg-outline-variant rounded-full mt-1 shrink-0"></div>
            <div>
              <p className="font-bold text-sm text-on-surface">Inactive State (OFF)</p>
              <p className="text-on-surface-variant mt-1 text-sm">Disables the module. Users will see a 'Coming Soon' placeholder or the entry point hidden.</p>
            </div>
          </div>
          <div className="flex items-start gap-md">
            <div className="w-3 h-12 bg-secondary rounded-full mt-1 shrink-0 shadow-[0_0_8px_rgba(91,89,140,0.4)]"></div>
            <div>
              <p className="font-bold text-sm text-on-surface">Inherited Settings</p>
              <p className="text-on-surface-variant mt-1 text-sm">Some flags locked based on license tier (Enterprise vs Partner). Check tier settings.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function AnalyticsTab() {
  return (
    <div className="space-y-xl animate-in fade-in duration-300">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="font-h1 text-h1 mb-xs">Platform Analytics</h2>
          <p className="font-body-lg text-on-surface-variant max-w-2xl">Monitor real-time user growth, organizational distribution, and detailed engagement metrics.</p>
        </div>
        <div className="flex gap-md">
          <button className="neumorphic-card px-lg py-sm bg-white rounded-xl font-label-caps text-label-caps flex items-center gap-xs hover:scale-95 transition-transform text-sm">
            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>download</span>Export PDF
          </button>
          <button className="px-lg py-sm bg-primary text-white rounded-xl font-label-caps text-label-caps shadow-lg shadow-primary/20 hover:scale-95 transition-transform text-sm" style={{boxShadow: '0 0 15px rgba(70,72,212,0.4)'}}>
            Live Monitor
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-grid-gutter">
        <div className="glass-panel p-md rounded-xl tilt-card">
          <p className="font-label-caps text-label-caps text-on-surface-variant mb-xs">Total Active Users</p>
          <div className="flex items-end gap-sm">
            <span className="font-h2 text-h2 text-primary">12,482</span>
            <span className="text-green-500 font-data-mono text-sm flex items-center mb-xs">
              <span className="material-symbols-outlined" style={{fontSize: '14px'}}>trending_up</span>+14%
            </span>
          </div>
        </div>
        <div className="glass-panel p-md rounded-xl tilt-card">
          <p className="font-label-caps text-label-caps text-on-surface-variant mb-xs">Daily Completion Rate</p>
          <div className="flex items-end gap-sm">
            <span className="font-h2 text-h2 text-secondary">78.4%</span>
            <span className="text-green-500 font-data-mono text-sm flex items-center mb-xs">
              <span className="material-symbols-outlined" style={{fontSize: '14px'}}>trending_up</span>+2%
            </span>
          </div>
        </div>
        <div className="glass-panel p-md rounded-xl tilt-card">
          <p className="font-label-caps text-label-caps text-on-surface-variant mb-xs">Avg. Session Time</p>
          <div className="flex items-end gap-sm">
            <span className="font-h2 text-h2 text-on-surface">42m</span>
            <span className="text-error font-data-mono text-sm flex items-center mb-xs">
              <span className="material-symbols-outlined" style={{fontSize: '14px'}}>trending_down</span>-5%
            </span>
          </div>
        </div>
        <div className="glass-panel p-md rounded-xl tilt-card">
          <p className="font-label-caps text-label-caps text-on-surface-variant mb-xs">New Organizations</p>
          <div className="flex items-end gap-sm">
            <span className="font-h2 text-h2 text-primary-container">24</span>
            <span className="text-primary-container font-data-mono text-sm flex items-center mb-xs">
              <span className="material-symbols-outlined" style={{fontSize: '14px'}}>fiber_new</span>This Month
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-xl">
        <div className="col-span-2 glass-panel p-lg rounded-xl tilt-card" style={{minHeight: '300px'}}>
          <div className="flex justify-between items-start mb-lg">
            <div>
              <h3 className="font-h3 text-h3">User Growth Trend</h3>
              <p className="text-sm text-on-surface-variant">Last 6 months performance</p>
            </div>
            <select className="bg-surface-container-low border-none rounded-lg inset-input text-sm font-label-caps text-label-caps px-md py-xs">
              <option>Monthly</option>
              <option>Weekly</option>
            </select>
          </div>
          <div className="flex items-end justify-around pb-md" style={{height: '200px'}}>
            <div className="flex flex-col items-center justify-end gap-xs w-12 h-full"><div className="w-full bg-primary/70 rounded-t-lg shadow-[0_0_15px_rgba(70,72,212,0.5)]" style={{height: '38%'}}></div><span className="font-data-mono text-[10px] text-outline">JAN</span></div>
            <div className="flex flex-col items-center justify-end gap-xs w-12 h-full"><div className="w-full bg-primary/75 rounded-t-lg shadow-[0_0_15px_rgba(70,72,212,0.5)]" style={{height: '52%'}}></div><span className="font-data-mono text-[10px] text-outline">FEB</span></div>
            <div className="flex flex-col items-center justify-end gap-xs w-12 h-full"><div className="w-full bg-primary/80 rounded-t-lg shadow-[0_0_15px_rgba(70,72,212,0.5)]" style={{height: '67%'}}></div><span className="font-data-mono text-[10px] text-outline">MAR</span></div>
            <div className="flex flex-col items-center justify-end gap-xs w-12 h-full"><div className="w-full bg-primary/82 rounded-t-lg shadow-[0_0_15px_rgba(70,72,212,0.5)]" style={{height: '60%'}}></div><span className="font-data-mono text-[10px] text-outline">APR</span></div>
            <div className="flex flex-col items-center justify-end gap-xs w-12 h-full"><div className="w-full bg-primary/90 rounded-t-lg shadow-[0_0_15px_rgba(70,72,212,0.5)]" style={{height: '83%'}}></div><span className="font-data-mono text-[10px] text-outline">MAY</span></div>
            <div className="flex flex-col items-center justify-end gap-xs w-12 h-full"><div className="w-full bg-primary rounded-t-lg shadow-[0_0_15px_rgba(70,72,212,0.5)]" style={{height: '100%'}}></div><span className="font-data-mono text-[10px] text-outline">JUN</span></div>
          </div>
        </div>
        <div className="glass-panel p-lg rounded-xl tilt-card flex flex-col">
          <h3 className="font-h3 text-h3 mb-xs">Org Distribution</h3>
          <p className="text-sm text-on-surface-variant mb-lg">Market segment breakdown</p>
          <div className="flex flex-col items-center flex-1 justify-center">
            <div className="relative w-36 h-36 rounded-full flex items-center justify-center" style={{border: '24px solid #6063ee'}}>
              <div className="absolute inset-0 rounded-full" style={{border: '24px solid #e3dfff', clipPath: 'polygon(50% 0%,100% 0%,100% 50%,50% 50%)'}}></div>
              <div className="flex flex-col items-center"><span className="font-h3 text-h3">64%</span><span className="font-label-caps text-[10px] text-on-surface-variant">CORP</span></div>
            </div>
            <div className="mt-xl w-full space-y-sm">
              <div className="flex items-center justify-between"><div className="flex items-center gap-xs"><div className="w-3 h-3 rounded-full bg-primary-container"></div><span className="text-sm">Corporate</span></div><span className="font-data-mono text-sm">64%</span></div>
              <div className="flex items-center justify-between"><div className="flex items-center gap-xs"><div className="w-3 h-3 rounded-full bg-secondary-fixed"></div><span className="text-sm">Higher Ed</span></div><span className="font-data-mono text-sm">22%</span></div>
              <div className="flex items-center justify-between"><div className="flex items-center gap-xs"><div className="w-3 h-3 rounded-full bg-tertiary-container"></div><span className="text-sm">Government</span></div><span className="font-data-mono text-sm">14%</span></div>
            </div>
          </div>
        </div>
      </div>

      <div className="glass-panel rounded-xl overflow-hidden shadow-xl tilt-card">
        <div className="px-lg py-md border-b border-white/20 flex justify-between items-center bg-white/10">
          <h3 className="font-h3 text-h3">Usage per Organization</h3>
          <button className="inset-input pl-9 pr-md py-xs bg-surface-container-low rounded-lg font-label-caps text-label-caps text-sm relative">
            <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline" style={{fontSize: '16px'}}>filter_list</span>Filter
          </button>
        </div>
        <table className="w-full text-left">
          <thead>
            <tr className="bg-surface-container-lowest font-label-caps text-label-caps text-on-surface-variant">
              <th className="px-lg py-md">Organization</th>
              <th className="px-lg py-md">Active Users</th>
              <th className="px-lg py-md">Storage Used</th>
              <th className="px-lg py-md">Health Score</th>
              <th className="px-lg py-md text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            <tr className="hover:bg-white/30 transition-colors">
              <td className="px-lg py-md">
                <div className="flex items-center gap-md">
                  <div className="w-10 h-10 rounded bg-indigo-100 flex items-center justify-center text-primary font-bold text-sm">NV</div>
                  <div>
                    <div className="font-bold text-sm">Nexus Ventures</div>
                    <div className="text-xs text-on-surface-variant">Premium Plan</div>
                  </div>
                </div>
              </td>
              <td className="px-lg py-md text-sm">2,450</td>
              <td className="px-lg py-md">
                <div className="h-2 w-28 bg-surface-container rounded-full overflow-hidden mb-1"><div className="h-full bg-primary" style={{width: '75%'}}></div></div>
                <span className="text-xs text-on-surface-variant">750GB / 1TB</span>
              </td>
              <td className="px-lg py-md"><span className="px-2 py-1 bg-green-100 text-green-700 rounded-lg text-xs font-bold">Excellent</span></td>
              <td className="px-lg py-md text-right"><button className="p-sm hover:bg-primary/10 rounded-full text-primary"><span className="material-symbols-outlined">more_vert</span></button></td>
            </tr>
            <tr className="hover:bg-white/30 transition-colors">
              <td className="px-lg py-md">
                <div className="flex items-center gap-md">
                  <div className="w-10 h-10 rounded bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-sm">AU</div>
                  <div>
                    <div className="font-bold text-sm">Apex University</div>
                    <div className="text-xs text-on-surface-variant">Edu Enterprise</div>
                  </div>
                </div>
              </td>
              <td className="px-lg py-md text-sm">4,812</td>
              <td className="px-lg py-md">
                <div className="h-2 w-28 bg-surface-container rounded-full overflow-hidden mb-1"><div className="h-full bg-primary" style={{width: '45%'}}></div></div>
                <span className="text-xs text-on-surface-variant">2.2TB / 5TB</span>
              </td>
              <td className="px-lg py-md"><span className="px-2 py-1 bg-green-100 text-green-700 rounded-lg text-xs font-bold">Stable</span></td>
              <td className="px-lg py-md text-right"><button className="p-sm hover:bg-primary/10 rounded-full text-primary"><span className="material-symbols-outlined">more_vert</span></button></td>
            </tr>
            <tr className="hover:bg-white/30 transition-colors">
              <td className="px-lg py-md">
                <div className="flex items-center gap-md">
                  <div className="w-10 h-10 rounded bg-amber-100 flex items-center justify-center text-amber-600 font-bold text-sm">SL</div>
                  <div>
                    <div className="font-bold text-sm">Skyline Logistics</div>
                    <div className="text-xs text-on-surface-variant">Standard Plan</div>
                  </div>
                </div>
              </td>
              <td className="px-lg py-md text-sm">890</td>
              <td className="px-lg py-md">
                <div className="h-2 w-28 bg-surface-container rounded-full overflow-hidden mb-1"><div className="h-full bg-error" style={{width: '92%', boxShadow: '0 0 6px rgba(186,26,26,0.4)'}}></div></div>
                <span className="text-xs text-error">460GB / 500GB</span>
              </td>
              <td className="px-lg py-md"><span className="px-2 py-1 bg-amber-100 text-amber-700 rounded-lg text-xs font-bold">Warning</span></td>
              <td className="px-lg py-md text-right"><button className="p-sm hover:bg-primary/10 rounded-full text-primary"><span className="material-symbols-outlined">more_vert</span></button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --- MODALS ---
function CreateOrganizationModal({ open, onClose, onCreated }) {
  const { showToast } = useToast();
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ name: "", type: "college", domain: "", slug: "", super_admin_email: "", moodle_setup: "manual" });

  if (!open) return null;

  const canNext = (step === 1 && form.name.trim() && form.domain.trim()) || step === 2 || step === 3;

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-md bg-on-background/40 backdrop-blur-md">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in duration-300">
        <div className="px-xl py-lg border-b border-surface-container flex justify-between items-center">
          <div>
            <h2 className="text-h2 text-[24px] font-bold text-on-surface">Create New Organization</h2>
            <p className="text-on-surface-variant text-sm mt-1">Set up a new educational or corporate partner.</p>
          </div>
          <button onClick={onClose} className="w-10 h-10 rounded-full hover:bg-surface-container flex items-center justify-center text-outline">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        
        <div className="p-xl space-y-lg">
          {/* Progress Indicator */}
          <div className="flex items-center gap-md mb-xl">
            <div className={`flex items-center gap-xs ${step >= 1 ? 'opacity-100' : 'opacity-40'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= 1 ? 'bg-primary text-white' : 'bg-surface-container text-on-surface-variant'}`}>1</div>
              <span className="font-bold text-sm">Basic Info</span>
            </div>
            <div className="h-px flex-1 bg-surface-container"></div>
            <div className={`flex items-center gap-xs ${step >= 2 ? 'opacity-100' : 'opacity-40'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= 2 ? 'bg-primary text-white' : 'bg-surface-container text-on-surface-variant'}`}>2</div>
              <span className="font-bold text-sm">Admin Setup</span>
            </div>
            <div className="h-px flex-1 bg-surface-container"></div>
            <div className={`flex items-center gap-xs ${step >= 3 ? 'opacity-100' : 'opacity-40'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${step >= 3 ? 'bg-primary text-white' : 'bg-surface-container text-on-surface-variant'}`}>3</div>
              <span className="font-bold text-sm">Review</span>
            </div>
          </div>

          {step === 1 && (
            <div className="grid grid-cols-2 gap-lg">
              <div className="col-span-2">
                <label className="block text-[11px] font-bold text-outline mb-2 uppercase tracking-widest">Organization Name</label>
                <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="w-full px-md py-3 rounded-xl border border-outline-variant focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all inset-input" placeholder="e.g. Stanford University" type="text" />
              </div>
              <div className="col-span-1">
                <label className="block text-[11px] font-bold text-outline mb-2 uppercase tracking-widest">Organization Type</label>
                <select value={form.type} onChange={e => setForm({...form, type: e.target.value})} className="w-full px-md py-3 rounded-xl border border-outline-variant focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all inset-input">
                  <option value="college">College</option>
                  <option value="company">Company</option>
                </select>
              </div>
              <div className="col-span-1">
                <label className="block text-[11px] font-bold text-outline mb-2 uppercase tracking-widest">Custom Domain</label>
                <input value={form.domain} onChange={e => setForm({...form, domain: e.target.value})} className="w-full px-md py-3 rounded-xl border border-outline-variant focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all inset-input" placeholder="e.g. stanford.edu" type="text" />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-lg">
              <div>
                <label className="block text-[11px] font-bold text-outline mb-2 uppercase tracking-widest">Super Admin Email (Optional)</label>
                <input value={form.super_admin_email} onChange={e => setForm({...form, super_admin_email: e.target.value})} className="w-full px-md py-3 rounded-xl border border-outline-variant focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all inset-input" placeholder="admin@example.edu" type="email" />
                <p className="text-xs text-outline mt-2">If provided, an invitation token will be emailed to onboard via /accept-invite.</p>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-lg">
              <div>
                <label className="block text-[11px] font-bold text-outline mb-2 uppercase tracking-widest">Moodle Setup Mode</label>
                <select value={form.moodle_setup} onChange={e => setForm({...form, moodle_setup: e.target.value})} className="w-full px-md py-3 rounded-xl border border-outline-variant focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all inset-input">
                  <option value="manual">Manual Configuration</option>
                  <option value="auto">Automatic (Create Moodle Category)</option>
                </select>
              </div>
            </div>
          )}
        </div>

        <div className="px-xl py-lg bg-surface-container-low flex justify-end gap-md">
          <button onClick={onClose} disabled={submitting} className="px-lg py-3 text-on-surface-variant font-bold hover:text-on-surface transition-colors">Cancel</button>
          {step > 1 && <button onClick={() => setStep(s=>s-1)} disabled={submitting} className="px-lg py-3 text-on-surface-variant font-bold hover:text-on-surface transition-colors border border-outline-variant rounded-xl bg-white">Back</button>}
          {step < 3 ? (
            <button onClick={() => setStep(s=>s+1)} disabled={!canNext} className="bg-primary hover:bg-primary/90 text-white px-xl py-3 rounded-xl font-bold shadow-lg hover:shadow-primary/20 transition-all disabled:opacity-50">Next Step</button>
          ) : (
            <button 
              disabled={submitting || !form.name.trim() || !form.domain.trim()} 
              onClick={async () => {
                setSubmitting(true);
                try {
                  await platformApi.createOrganization({
                    name: form.name.trim(), type: form.type, domain: form.domain.trim(),
                    slug: form.slug.trim() || null, super_admin_email: form.super_admin_email.trim() || null,
                    moodle_setup: form.moodle_setup,
                  });
                  showToast("Organization created", "success");
                  onCreated?.();
                } catch (err) {
                  showToast(err.response?.data?.detail || "Failed to create organization", "error");
                } finally {
                  setSubmitting(false);
                }
              }}
              className="bg-primary hover:bg-primary/90 text-white px-xl py-3 rounded-xl font-bold shadow-lg hover:shadow-primary/20 transition-all disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create Organization'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function InviteAdminModal({ open, onClose, onInvited }) {
  const { showToast } = useToast();
  const [orgs, setOrgs] = useState([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ org_id: "", email: "", role: "super_admin" });

  useEffect(() => {
    if (!open) return;
    setSubmitting(false);
    setForm({ org_id: "", email: "", role: "super_admin" });

    setLoadingOrgs(true);
    platformApi.listOrganizations({ limit: 100 })
      .then(res => setOrgs(res.data.orgs))
      .catch(() => showToast("Failed to load organizations", "error"))
      .finally(() => setLoadingOrgs(false));
  }, [open, showToast]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email.trim()) return showToast("Email is required", "error");

    setSubmitting(true);
    try {
      await platformApi.inviteAdmin({
        email: form.email.trim(),
        role: form.role,
        org_id: form.org_id || null
      });
      showToast("Invitation sent successfully", "success");
      onInvited();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to send invitation", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-md bg-on-background/20 backdrop-blur-sm">
      <div className="bg-white w-full max-w-[560px] rounded-[32px] shadow-2xl flex flex-col items-center relative overflow-hidden p-xl">
        <button onClick={onClose} className="absolute top-sm right-sm p-base text-outline hover:text-on-surface transition-colors">
          <span className="material-symbols-outlined">close</span>
        </button>

        <div className="w-16 h-16 bg-[#6366f1] rounded-2xl flex items-center justify-center shadow-lg mb-sm">
          <span className="text-white font-bold text-h3 tracking-tight">TL</span>
        </div>

        <div className="text-center mb-lg">
          <h1 className="font-h3 text-[24px] font-bold text-on-surface mb-xs">Invite Organization Admin</h1>
          <p className="text-on-surface-variant font-body-md">Send an invitation to join the platform administration.</p>
        </div>

        <form onSubmit={handleSubmit} className="w-full space-y-md">
          <div className="space-y-xs">
            <label className="font-label-caps text-[12px] font-bold text-on-surface-variant px-xs uppercase tracking-wider">Email Address</label>
            <div className="relative group">
              <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors">mail</span>
              <input 
                type="email" 
                required 
                value={form.email}
                onChange={e => setForm({...form, email: e.target.value})}
                className="w-full pl-xl pr-md py-sm bg-surface-container-low border-transparent rounded-xl font-body-md text-on-surface focus:border-primary focus:ring-0 inset-input transition-all hover:shadow-[0_0_0_2px_rgba(99,102,241,0.1)]" 
                placeholder="admin@example.com"
              />
            </div>
          </div>

          <div className="space-y-xs">
            <label className="font-label-caps text-[12px] font-bold text-on-surface-variant px-xs uppercase tracking-wider">Role</label>
            <div className="relative group">
              <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors">badge</span>
              <select 
                value={form.role}
                onChange={e => setForm({...form, role: e.target.value})}
                className="w-full pl-xl pr-md py-sm bg-surface-container-low border-transparent rounded-xl font-body-md text-on-surface focus:border-primary focus:ring-0 inset-input transition-all hover:shadow-[0_0_0_2px_rgba(99,102,241,0.1)] appearance-none"
              >
                <option value="super_admin">Platform Super Admin</option>
                <option value="org_admin">Organization Admin</option>
              </select>
            </div>
          </div>

          {form.role === 'org_admin' && (
            <div className="space-y-xs">
              <label className="font-label-caps text-[12px] font-bold text-on-surface-variant px-xs uppercase tracking-wider">Organization</label>
              <div className="relative group">
                <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors">corporate_fare</span>
                <select 
                  required
                  value={form.org_id}
                  onChange={e => setForm({...form, org_id: e.target.value})}
                  className="w-full pl-xl pr-md py-sm bg-surface-container-low border-transparent rounded-xl font-body-md text-on-surface focus:border-primary focus:ring-0 inset-input transition-all hover:shadow-[0_0_0_2px_rgba(99,102,241,0.1)] appearance-none"
                >
                  <option value="">Select Organization</option>
                  {orgs.map(o => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <button 
            type="submit" 
            disabled={submitting || (form.role === 'org_admin' && !form.org_id)}
            className="w-full bg-primary text-white py-md rounded-xl font-h3 text-body-md font-semibold hover:shadow-indigo-500/20 shadow-lg transform active:scale-[0.98] transition-all flex items-center justify-center gap-xs hover:bg-primary-container hover:scale-[1.02] duration-300 ease-out mt-lg disabled:opacity-50"
          >
            {submitting ? 'Sending...' : 'Send Invitation'}
            <span className="material-symbols-outlined">send</span>
          </button>
        </form>

        <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
      </div>
    </div>
  );
}

function SettingsTab() {
  const { showToast } = useToast();
  const [saving, setSaving] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      showToast("Settings saved successfully", "success");
      setSaving(false);
    }, 1000);
  };

  const Toggle = ({ active, defaultOn }) => {
    const [isOn, setIsOn] = useState(defaultOn || active);
    return (
      <div className={`tog ${isOn ? 'on' : ''}`} onClick={() => setIsOn(!isOn)}></div>
    );
  };

  return (
    <div className="p-container-padding space-y-lg pb-xl relative z-10">
      <div>
        <h2 className="font-h1 text-h1">Settings</h2>
        <p className="text-on-surface-variant text-body-lg mt-sm">Configure your global platform preferences and security policies.</p>
      </div>
      <div className="grid grid-cols-2 gap-grid-gutter">
        <div className="neu glass p-lg rounded-2xl space-y-md">
          <div className="flex items-center gap-sm mb-md">
            <span className="material-symbols-outlined text-primary p-sm bg-primary/10 rounded-xl" style={{fontSize: '20px'}}>tune</span>
            <h3 className="font-h3 text-h3">General</h3>
          </div>
          <div className="space-y-xs">
            <label className="font-label-caps text-label-caps text-on-surface-variant">Platform Name</label>
            <input className="w-full px-md py-sm border border-outline-variant rounded-xl focus:ring-2 focus:ring-primary/20 focus:outline-none text-sm" defaultValue="Telite LMS" />
          </div>
          <div className="space-y-xs">
            <label className="font-label-caps text-label-caps text-on-surface-variant">Support Email</label>
            <input className="w-full px-md py-sm border border-outline-variant rounded-xl focus:ring-2 focus:ring-primary/20 focus:outline-none text-sm" defaultValue="support@telite.io" />
          </div>
          <div className="space-y-xs">
            <label className="font-label-caps text-label-caps text-on-surface-variant">Default Timezone</label>
            <select className="w-full px-md py-sm border border-outline-variant rounded-xl focus:ring-2 focus:ring-primary/20 focus:outline-none text-sm">
              <option>UTC+0</option>
              <option>UTC+5:30 (IST)</option>
              <option>UTC-5 (EST)</option>
            </select>
          </div>
          <div className="space-y-xs">
            <label className="font-label-caps text-label-caps text-on-surface-variant">Platform Logo URL</label>
            <input className="w-full px-md py-sm border border-outline-variant rounded-xl focus:ring-2 focus:ring-primary/20 focus:outline-none text-sm" placeholder="https://..." />
          </div>
          <button onClick={handleSave} disabled={saving} className="w-full bg-primary text-white py-sm rounded-xl font-semibold mt-sm hover:bg-primary-container transition-all text-sm disabled:opacity-50">
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
        <div className="neu glass p-lg rounded-2xl space-y-md">
          <div className="flex items-center gap-sm mb-md">
            <span className="material-symbols-outlined text-secondary p-sm bg-secondary/10 rounded-xl" style={{fontSize: '20px'}}>security</span>
            <h3 className="font-h3 text-h3">Security</h3>
          </div>
          <div className="flex items-center justify-between p-md bg-surface-container-low rounded-xl">
            <div><p className="font-semibold text-sm">Two-Factor Authentication</p><p className="text-xs text-on-surface-variant">Require 2FA for all admin accounts</p></div>
            <Toggle defaultOn={true} />
          </div>
          <div className="flex items-center justify-between p-md bg-surface-container-low rounded-xl">
            <div><p className="font-semibold text-sm">Session Timeout (30 min)</p><p className="text-xs text-on-surface-variant">Auto-logout after inactivity</p></div>
            <Toggle defaultOn={true} />
          </div>
          <div className="flex items-center justify-between p-md bg-surface-container-low rounded-xl">
            <div><p className="font-semibold text-sm">Audit Logging</p><p className="text-xs text-on-surface-variant">Log all administrative actions</p></div>
            <Toggle defaultOn={true} />
          </div>
          <div className="flex items-center justify-between p-md bg-surface-container-low rounded-xl">
            <div><p className="font-semibold text-sm">IP Allowlist</p><p className="text-xs text-on-surface-variant">Restrict access to known IP ranges</p></div>
            <Toggle defaultOn={false} />
          </div>
          <div className="flex items-center justify-between p-md bg-surface-container-low rounded-xl">
            <div><p className="font-semibold text-sm">Login Attempt Lockout</p><p className="text-xs text-on-surface-variant">Lock after 5 failed attempts</p></div>
            <Toggle defaultOn={true} />
          </div>
        </div>
      </div>
      {/* Notification Settings */}
      <div className="neu glass p-lg rounded-2xl mt-grid-gutter">
        <div className="flex items-center gap-sm mb-md">
          <span className="material-symbols-outlined text-tertiary p-sm bg-tertiary/10 rounded-xl" style={{fontSize: '20px'}}>notifications_active</span>
          <h3 className="font-h3 text-h3">Notifications</h3>
        </div>
        <div className="grid grid-cols-3 gap-md">
          <div className="flex items-center justify-between p-md bg-surface-container-low rounded-xl">
            <div><p className="font-semibold text-sm">Email Alerts</p><p className="text-xs text-on-surface-variant">System events via email</p></div>
            <Toggle defaultOn={true} />
          </div>
          <div className="flex items-center justify-between p-md bg-surface-container-low rounded-xl">
            <div><p className="font-semibold text-sm">Security Alerts</p><p className="text-xs text-on-surface-variant">Critical security events</p></div>
            <Toggle defaultOn={true} />
          </div>
          <div className="flex items-center justify-between p-md bg-surface-container-low rounded-xl">
            <div><p className="font-semibold text-sm">Sync Reports</p><p className="text-xs text-on-surface-variant">Daily Moodle sync digest</p></div>
            <Toggle defaultOn={false} />
          </div>
        </div>
      </div>
    </div>
  );
}

function HelpTab() {
  const navigate = useNavigate();

  return (
    <div className="p-container-padding space-y-xl pb-xl relative z-10">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-[2rem] p-xl glass text-center flex flex-col items-center justify-center" style={{minHeight: '360px', background: 'linear-gradient(135deg,rgba(70,72,212,0.06) 0%,rgba(91,89,140,0.06) 100%)'}}>
        <h2 className="font-h1 text-h1 text-on-background mb-sm">How can we help you?</h2>
        <p className="font-body-lg text-on-surface-variant mb-lg max-w-2xl">Manage your organizations, Moodle integrations, and audit logs with professional precision.</p>
        <div className="relative w-full max-w-xl mx-auto mb-lg">
          <span className="material-symbols-outlined absolute left-md top-1/2 -translate-y-1/2 text-outline">search</span>
          <input className="w-full pl-xl pr-20 py-sm rounded-full bg-white border-none focus:ring-2 focus:ring-primary/50 text-body-md focus:outline-none inset-input shadow-sm" placeholder="Search documentation..." />
          <div className="absolute right-sm top-1/2 -translate-y-1/2 px-xs py-0.5 bg-white border border-outline-variant rounded-lg font-data-mono text-[10px] text-outline">⌘K</div>
        </div>
        <div className="flex flex-wrap justify-center gap-sm">
          <button className="px-md py-sm bg-primary text-on-primary rounded-xl font-bold neu flex items-center gap-xs text-sm"><span className="material-symbols-outlined" style={{fontSize: '17px'}}>menu_book</span>Read full docs</button>
          <button className="px-md py-sm glass bg-white/20 text-on-background rounded-xl font-bold hover:bg-white/40 transition-all border border-white/40 flex items-center gap-xs text-sm"><span className="material-symbols-outlined" style={{fontSize: '17px'}}>play_circle</span>Watch tutorials</button>
          <button className="px-md py-sm glass bg-white/20 text-on-background rounded-xl font-bold hover:bg-white/40 transition-all border border-white/40 flex items-center gap-xs text-sm"><span className="material-symbols-outlined" style={{fontSize: '17px'}}>contact_support</span>Contact support</button>
        </div>
      </div>
      {/* Quick Access */}
      <div className="grid grid-cols-4 gap-grid-gutter">
        <div onClick={() => navigate('/platform-admin/organizations')} className="glass p-md rounded-xl cursor-pointer flex flex-col items-center text-center group hover:shadow-lg transition-all hover:-translate-y-1">
          <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary mb-sm group-hover:scale-110 transition-transform"><span className="material-symbols-outlined">domain</span></div>
          <h3 className="font-bold text-sm mb-xs">Organizations</h3>
          <p className="font-label-caps text-[10px] text-on-surface-variant">Multi-tenant Management</p>
        </div>
        <div onClick={() => navigate('/platform-admin/admins')} className="glass p-md rounded-xl cursor-pointer flex flex-col items-center text-center group hover:shadow-lg transition-all hover:-translate-y-1">
          <div className="w-12 h-12 bg-secondary-container/20 rounded-xl flex items-center justify-center text-secondary mb-sm group-hover:scale-110 transition-transform"><span className="material-symbols-outlined">admin_panel_settings</span></div>
          <h3 className="font-bold text-sm mb-xs">Admin Control</h3>
          <p className="font-label-caps text-[10px] text-on-surface-variant">Permissions & Roles</p>
        </div>
        <div onClick={() => navigate('/platform-admin/moodle')} className="glass p-md rounded-xl cursor-pointer flex flex-col items-center text-center group hover:shadow-lg transition-all hover:-translate-y-1">
          <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary mb-sm group-hover:scale-110 transition-transform"><span className="material-symbols-outlined">sync</span></div>
          <h3 className="font-bold text-sm mb-xs">Moodle Sync</h3>
          <p className="font-label-caps text-[10px] text-on-surface-variant">Integration Hub</p>
        </div>
        <div onClick={() => navigate('/platform-admin/features')} className="glass p-md rounded-xl cursor-pointer flex flex-col items-center text-center group hover:shadow-lg transition-all hover:-translate-y-1">
          <div className="w-12 h-12 bg-tertiary-container/10 rounded-xl flex items-center justify-center text-tertiary mb-sm group-hover:scale-110 transition-transform"><span className="material-symbols-outlined">toggle_on</span></div>
          <h3 className="font-bold text-sm mb-xs">Feature Flags</h3>
          <p className="font-label-caps text-[10px] text-on-surface-variant">System Capabilities</p>
        </div>
      </div>
      {/* Content */}
      <div className="grid grid-cols-3 gap-xl">
        <div className="col-span-2 space-y-xl">
          <div className="space-y-md">
            <div className="flex items-center gap-xs"><span className="material-symbols-outlined text-primary">auto_stories</span><h2 className="font-h3 text-h3">Step-by-Step Guides</h2></div>
            <details className="glass rounded-xl group" open style={{cursor: 'pointer'}}>
              <summary className="p-md flex justify-between items-center list-none select-none">
                <span className="font-bold text-sm">Organization Creation & Onboarding</span>
                <span className="material-symbols-outlined group-open:-rotate-180 transition-transform duration-300">expand_more</span>
              </summary>
              <div className="px-md pb-md text-on-surface-variant text-sm space-y-sm border-t border-white/20 pt-sm">
                <p>Follow these steps to initialize a new tenant environment:</p>
                <ol className="list-decimal list-inside space-y-xs ml-sm">
                  <li>Navigate to "Organizations" and click "New Organization".</li>
                  <li>Define organizational domain and metadata tags.</li>
                  <li>Assign the primary Administrator and set resource quotas.</li>
                </ol>
              </div>
            </details>
            <details className="glass rounded-xl group" style={{cursor: 'pointer'}}>
              <summary className="p-md flex justify-between items-center list-none select-none">
                <span className="font-bold text-sm">Moodle Sync Resolution Workflows</span>
                <span className="material-symbols-outlined group-open:-rotate-180 transition-transform duration-300">expand_more</span>
              </summary>
              <div className="px-md pb-md text-on-surface-variant text-sm border-t border-white/20 pt-sm">
                <p>Troubleshoot common synchronization issues between Telite and Moodle instances.</p>
              </div>
            </details>
            <details className="glass rounded-xl group" style={{cursor: 'pointer'}}>
              <summary className="p-md flex justify-between items-center list-none select-none">
                <span className="font-bold text-sm">Audit Log Export for Compliance</span>
                <span className="material-symbols-outlined group-open:-rotate-180 transition-transform duration-300">expand_more</span>
              </summary>
              <div className="px-md pb-md text-on-surface-variant text-sm border-t border-white/20 pt-sm">
                <p>Detailed steps on filtering and exporting enterprise-grade logs for compliance.</p>
              </div>
            </details>
          </div>
          <div className="space-y-md">
            <div className="flex items-center gap-xs"><span className="material-symbols-outlined text-primary">keyboard</span><h2 className="font-h3 text-h3">Global Keyboard Shortcuts</h2></div>
            <div className="glass rounded-xl overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-primary/5 border-b border-white/20">
                  <tr>
                    <th className="p-md font-label-caps text-label-caps text-outline text-xs">Action</th>
                    <th className="p-md font-label-caps text-label-caps text-outline text-xs">Shortcut</th>
                    <th className="p-md font-label-caps text-label-caps text-outline text-xs">Scope</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  <tr className="hover:bg-white/10"><td className="p-md text-sm">Quick Search</td><td className="p-md"><kbd className="bg-surface-container-highest px-xs py-0.5 rounded border border-outline-variant font-data-mono text-xs">⌘ K</kbd></td><td className="p-md text-xs text-on-surface-variant">Global</td></tr>
                  <tr className="hover:bg-white/10"><td className="p-md text-sm">New Organization</td><td className="p-md"><kbd className="bg-surface-container-highest px-xs py-0.5 rounded border border-outline-variant font-data-mono text-xs">⌥ N</kbd></td><td className="p-md text-xs text-on-surface-variant">Dashboard</td></tr>
                  <tr className="hover:bg-white/10"><td className="p-md text-sm">Export Audit Log</td><td className="p-md"><kbd className="bg-surface-container-highest px-xs py-0.5 rounded border border-outline-variant font-data-mono text-xs">⇧ E</kbd></td><td className="p-md text-xs text-on-surface-variant">Audit Page</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div className="space-y-xl">
          <div className="glass p-md rounded-[1.5rem] space-y-md">
            <h3 className="font-bold text-sm">Contact Support</h3>
            <div className="space-y-sm">
              <div className="flex items-center justify-between p-sm rounded-xl bg-white/30">
                <div className="flex items-center gap-sm"><span className="material-symbols-outlined text-primary" style={{fontSize: '18px'}}>chat_bubble</span><div><p className="text-sm font-bold">Live Chat</p><p className="text-[10px] text-on-surface-variant">2h avg response</p></div></div>
                <button className="text-xs text-primary font-bold">Start</button>
              </div>
              <div className="flex items-center justify-between p-sm rounded-xl bg-white/30">
                <div className="flex items-center gap-sm"><span className="material-symbols-outlined text-secondary" style={{fontSize: '18px'}}>mail</span><div><p className="text-sm font-bold">Email Ticket</p><p className="text-[10px] text-on-surface-variant">24h response</p></div></div>
                <button className="text-xs text-primary font-bold">Open</button>
              </div>
              <div className="flex items-center justify-between p-sm rounded-xl bg-error-container/10 border border-error/20">
                <div className="flex items-center gap-sm"><span className="material-symbols-outlined text-error" style={{fontSize: '18px'}}>emergency_home</span><div><p className="text-sm font-bold text-error">Critical Escalation</p><p className="text-[10px] text-error/70">24/7 Phone Support</p></div></div>
                <button className="text-xs text-error font-bold">Call</button>
              </div>
            </div>
          </div>
          <div className="glass p-md rounded-[1.5rem] space-y-md">
            <div className="flex items-center justify-between"><h3 className="font-bold text-sm">System Status</h3><span className="flex items-center gap-xs px-xs py-0.5 bg-green-100 text-green-700 rounded-full text-[10px] font-bold">ALL SYSTEMS LIVE</span></div>
            <div className="space-y-xs">
              <div className="flex items-center justify-between text-sm py-xs"><span className="text-on-surface-variant text-xs">Database Clusters</span><div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div></div>
              <div className="flex items-center justify-between text-sm py-xs"><span className="text-on-surface-variant text-xs">Moodle API Bridge</span><div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div></div>
              <div className="flex items-center justify-between text-sm py-xs"><span className="text-on-surface-variant text-xs">SMTP Relay</span><div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div></div>
              <div className="flex items-center justify-between text-sm py-xs"><span className="text-on-surface-variant text-xs">Cron Jobs</span><div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div></div>
            </div>
          </div>
          <div className="space-y-sm">
            <h3 className="font-label-caps text-label-caps text-outline px-xs text-xs">Admin Quick Links</h3>
            <div className="space-y-xs">
              <div onClick={() => navigate('/platform-admin')} className="flex items-center justify-between p-sm glass rounded-xl hover:bg-white/60 transition-all cursor-pointer group text-sm"><span>Overview Dashboard</span><span className="material-symbols-outlined text-sm opacity-0 group-hover:opacity-100 transition-opacity">arrow_forward</span></div>
              <div onClick={() => navigate('/platform-admin/organizations')} className="flex items-center justify-between p-sm glass rounded-xl hover:bg-white/60 transition-all cursor-pointer group text-sm"><span>New Org Wizard</span><span className="material-symbols-outlined text-sm opacity-0 group-hover:opacity-100 transition-opacity">arrow_forward</span></div>
              <div onClick={() => navigate('/platform-admin/moodle')} className="flex items-center justify-between p-sm glass rounded-xl hover:bg-white/60 transition-all cursor-pointer group text-sm"><span>Global Sync Status</span><span className="material-symbols-outlined text-sm opacity-0 group-hover:opacity-100 transition-opacity">arrow_forward</span></div>
            </div>
          </div>
        </div>
      </div>
      {/* Changelog Footer */}
      <div className="glass p-md rounded-2xl flex flex-col md:flex-row items-center gap-md">
        <div className="flex items-center gap-sm pr-md border-r border-white/20"><span className="bg-primary text-on-primary px-sm py-xs rounded-lg font-data-mono text-xs font-bold">v5.1.0</span><span className="font-label-caps text-label-caps text-outline text-xs">Latest Update</span></div>
        <div className="flex-1 flex flex-wrap gap-lg">
          <div className="flex items-center gap-xs"><span className="w-2 h-2 rounded-full bg-primary"></span><span className="text-sm font-bold">Multi-tenant Migration:</span><span className="text-sm text-on-surface-variant">Optimized data isolation layers.</span></div>
          <div className="flex items-center gap-xs"><span className="w-2 h-2 rounded-full bg-secondary"></span><span className="text-sm font-bold">Invitation Flow:</span><span className="text-sm text-on-surface-variant">Secure automated setup tokens.</span></div>
          <div className="flex items-center gap-xs"><span className="w-2 h-2 rounded-full bg-tertiary"></span><span className="text-sm font-bold">Security:</span><span className="text-sm text-on-surface-variant">CVE-2024-9981 Patch deployed.</span></div>
        </div>
        <button className="flex items-center gap-xs text-primary font-bold text-sm whitespace-nowrap">View Changelog <span className="material-symbols-outlined" style={{fontSize: '16px'}}>launch</span></button>
      </div>
    </div>
  );
}
