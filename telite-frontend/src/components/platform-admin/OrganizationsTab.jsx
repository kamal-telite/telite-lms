import { useState, useMemo } from "react";
import { useToast } from "../../components/common/ui";
import { downloadCSV } from "../../utils/csvExport";
import { useAdminStore } from "../../store/adminConsoleStore";

export default function OrganizationsTab({ searchQuery, showConfirm, onOpenCreateOrg, onViewOrg }) {
  const { organizations: orgs, updateOrgStatus, loadOrganizations } = useAdminStore();
  const { showToast } = useToast();
  const [activeFilter, setActiveFilter] = useState('all');
  const [filterPopoverOpen, setFilterPopoverOpen] = useState(false);
  const [filterState, setFilterState] = useState({ status: 'all', type: 'all' });

  const filteredOrgs = useMemo(() => {
    let result = orgs;
    if (activeFilter === 'college') result = result.filter(o => o.type?.toLowerCase() === 'college');
    else if (activeFilter === 'company') result = result.filter(o => o.type?.toLowerCase() === 'company');
    else if (activeFilter === 'inactive') result = result.filter(o => o.status?.toLowerCase() === 'inactive' || o.status?.toLowerCase() === 'suspended');
    
    if (filterState.status !== 'all') result = result.filter(o => o.status?.toLowerCase() === filterState.status);
    if (filterState.type !== 'all') result = result.filter(o => o.type?.toLowerCase() === filterState.type);
    
    if (searchQuery && searchQuery.length >= 2) {
      const lowerQ = searchQuery.toLowerCase();
      result = result.filter(o => o.name?.toLowerCase().includes(lowerQ) || o.domain?.toLowerCase().includes(lowerQ));
    }
    return result;
  }, [orgs, activeFilter, searchQuery, filterState]);

  const handleToggleStatus = async (org) => {
    const isSuspending = org.status === 'active';
    const confirmed = await showConfirm({
      title: isSuspending ? 'Suspend Organization?' : 'Restore Organization?',
      description: isSuspending
        ? `This will prevent all users at ${org.name} from logging in.`
        : `This will restore access for all users at ${org.name}.`,
      confirmLabel: isSuspending ? 'Suspend' : 'Restore',
      variant: isSuspending ? 'destructive' : 'default',
    });
    if (!confirmed) return;
    const newStatus = isSuspending ? 'suspended' : 'active';
    try {
      await updateOrgStatus(org.id, newStatus);
      showToast(`${org.name} ${newStatus}`, 'success');
    } catch (_err) {
      showToast('Failed to update status', 'error');
    }
  };

  const exportOrgsCSV = () => {
    const headers = ['ID', 'Name', 'Type', 'Domain', 'Status', 'User Count'];
    const rows = filteredOrgs.map(o => [o.id, o.name, o.type, o.domain, o.status, o.user_count || 0]);
    downloadCSV(rows, headers, `organizations-${Date.now()}.csv`);
    showToast('CSV exported successfully', 'success');
  };

  return (
    <div className="page" style={{display: 'block'}}>
      <div className="page-header">
        <div>
          <div className="page-title">Organizations</div>
          <div className="page-sub">Manage educational institutions and corporate partners.</div>
        </div>
        <button className="btn btn-primary" onClick={onOpenCreateOrg}>
          <span className="material-symbols-outlined" style={{fontSize: '16px'}}>add</span> New Organization
        </button>
      </div>

      <div className="filter-bar">
        <div style={{display: 'flex', gap: '8px'}}>
          {['all', 'college', 'company', 'inactive'].map(f => (
            <button 
              key={f}
              className={`filter-chip ${activeFilter === f ? 'active' : ''}`}
              onClick={() => setActiveFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <div style={{display: 'flex', gap: '8px', marginLeft: 'auto'}}>
          <button className="btn btn-secondary" onClick={exportOrgsCSV}>
            <span className="material-symbols-outlined" style={{fontSize: '14px'}}>download</span> Export CSV
          </button>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Organization</th>
            <th>Type</th>
            <th>Domain</th>
            <th>Users</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {filteredOrgs.map(org => (
            <tr key={org.id}>
              <td>
                <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                  <div className="avatar" style={{background: org.type?.toLowerCase() === 'college' ? 'var(--primary-lt)' : '#ECFDF5', color: org.type?.toLowerCase() === 'college' ? 'var(--primary)' : '#059669', fontSize: '12px'}}>
                    {(org.name || 'O').substring(0,2).toUpperCase()}
                  </div>
                  <span style={{fontWeight: 600, fontSize: '13px'}}>{org.name}</span>
                </div>
              </td>
              <td><span className={`badge ${org.type?.toLowerCase() === 'college' ? 'badge-indigo' : 'badge-gray'}`}>{org.type?.toUpperCase()}</span></td>
              <td style={{fontFamily: 'var(--fm)', fontSize: '12px'}}>{org.domain}</td>
              <td style={{fontFamily: 'var(--fm)'}}>{org.user_count || 0}</td>
              <td>
                <span className={`status-dot ${org.status?.toLowerCase() === 'active' ? 'active' : 'suspended'}`}>
                  {org.status === 'active' ? 'Active' : 'Suspended'}
                </span>
              </td>
              <td>
                <div style={{display: 'flex', gap: '6px'}}>
                  <button className="btn btn-sm btn-secondary" onClick={() => onViewOrg(org)}>View</button>
                  <button 
                    className={`btn btn-sm ${org.status === 'active' ? 'btn-danger' : 'btn-success'}`}
                    onClick={() => handleToggleStatus(org)}
                  >
                    {org.status === 'active' ? 'Suspend' : 'Restore'}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
