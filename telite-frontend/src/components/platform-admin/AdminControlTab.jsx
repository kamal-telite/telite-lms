import { useState, useMemo } from "react";
import { useToast } from "../../components/common/ui";
import { downloadCSV } from "../../utils/csvExport";
import { useAdminStore } from "../../store/adminConsoleStore";

export default function AdminControlTab({ searchQuery, showConfirm, onOpenInvite }) {
  const {
    admins,
    pendingInvitations,
    updateAdminStatus,
    deleteAdmin,
    loadAdmins,
  } = useAdminStore();
  const { showToast } = useToast();
  const [activeFilter, setActiveFilter] = useState('all');

  const filteredAdmins = useMemo(() => {
    let result = admins;
    if (activeFilter === 'active') result = result.filter(a => a.status === 'active');
    else if (activeFilter === 'suspended') result = result.filter(a => a.status === 'suspended');
    else if (activeFilter === 'pending') result = result.filter(a => a.status === 'pending');
    
    if (searchQuery && searchQuery.length >= 2) {
      const lowerQ = searchQuery.toLowerCase();
      result = result.filter(a => 
        (a.full_name || a.name || '').toLowerCase().includes(lowerQ) || 
        (a.email || '').toLowerCase().includes(lowerQ)
      );
    }
    return result;
  }, [admins, activeFilter, searchQuery]);

  const handleToggleStatus = async (admin) => {
    const isSuspending = admin.status === 'active';
    const confirmed = await showConfirm({
      title: isSuspending ? 'Suspend Admin?' : 'Restore Admin?',
      description: isSuspending
        ? `This will prevent ${admin.full_name || admin.email} from accessing the admin console.`
        : `This will restore access for ${admin.full_name || admin.email}.`,
      confirmLabel: isSuspending ? 'Suspend' : 'Restore',
      variant: isSuspending ? 'destructive' : 'default',
    });
    if (!confirmed) return;
    const newStatus = isSuspending ? 'suspended' : 'active';
    try {
      await updateAdminStatus(admin.id, newStatus);
      showToast(`Admin ${newStatus}`, 'success');
    } catch (_err) {
      showToast('Failed to update status', 'error');
    }
  };

  const handleDeleteAdmin = async (admin) => {
    const confirmed = await showConfirm({
      title: 'Delete Admin?',
      description: `This will permanently remove ${admin.full_name || admin.email} from the platform. This action cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'destructive',
    });
    if (!confirmed) return;
    try {
      await deleteAdmin(admin.id);
      showToast('Admin deleted successfully', 'success');
      loadAdmins();
    } catch (_err) {
      showToast('Failed to delete admin', 'error');
    }
  };

  const exportAdminsCSV = () => {
    const headers = ['ID', 'Name', 'Email', 'Role', 'Status', 'Organization'];
    const rows = filteredAdmins.map(a => [a.id, a.full_name || a.name, a.email, a.role, a.status, a.organization]);
    downloadCSV(rows, headers, `admins-${Date.now()}.csv`);
    showToast('CSV exported successfully', 'success');
  };

  return (
    <div className="page" style={{display: 'block'}}>
      <div className="page-header">
        <div>
          <div className="page-title">Admin Control</div>
          <div className="page-sub">Manage platform administrators and their permissions.</div>
        </div>
        <button className="btn btn-primary" onClick={onOpenInvite}>
          <span className="material-symbols-outlined" style={{fontSize: '16px'}}>person_add</span> Send Invitation
        </button>
      </div>

      <div className="filter-bar">
        <div style={{display: 'flex', gap: '8px'}}>
          {['all', 'active', 'suspended', 'pending'].map(f => (
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
          <button className="btn btn-secondary" onClick={exportAdminsCSV}>
            <span className="material-symbols-outlined" style={{fontSize: '14px'}}>download</span> Export CSV
          </button>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Admin</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {filteredAdmins.map(admin => (
            <tr key={admin.id}>
              <td>
                <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                  <div className="avatar" style={{background: 'var(--primary-lt)', color: 'var(--primary)', fontSize: '12px'}}>
                    {(admin.full_name || admin.email || 'A').substring(0, 2).toUpperCase()}
                  </div>
                  <span style={{fontWeight: 600, fontSize: '13px'}}>{admin.full_name || admin.email}</span>
                </div>
              </td>
              <td style={{fontFamily: 'var(--fm)', fontSize: '12px'}}>{admin.email}</td>
              <td><span className="badge badge-gray">{admin.role?.replace('_', ' ')}</span></td>
              <td>
                <span className={`status-dot ${admin.status === 'active' ? 'active' : 'suspended'}`}>
                  {admin.status === 'active' ? 'Active' : admin.status}
                </span>
              </td>
              <td>
                <div style={{display: 'flex', gap: '6px'}}>
                  <button 
                    className={`btn btn-sm ${admin.status === 'active' ? 'btn-danger' : 'btn-success'}`}
                    onClick={() => handleToggleStatus(admin)}
                  >
                    {admin.status === 'active' ? 'Suspend' : 'Restore'}
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDeleteAdmin(admin)}>
                    Delete
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
