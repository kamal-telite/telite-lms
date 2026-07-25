import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useToast } from "../../components/common/ui";
import { platformApi } from "../../services/platform";

export default function InviteAdminModal({ open, onClose, onInvited }) {
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
      .then(res => {
        const nextOrgs = Array.isArray(res.data?.organizations)
          ? res.data.organizations
          : Array.isArray(res.data?.orgs)
            ? res.data.orgs
            : Array.isArray(res.data)
              ? res.data
              : [];
        setOrgs(nextOrgs);
      })
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
      showToast(`Invitation sent to ${form.email}`, "success");
      onInvited?.();
      onClose();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to send invitation", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;
  return createPortal(
    <div className="overlay" onClick={onClose} style={{zIndex: 200}}>
      <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-title">Send Invitation</div>
            <div className="modal-sub">Invite a new admin to manage an organization.</div>
          </div>
          <button className="modal-close" onClick={onClose}><span className="material-symbols-outlined">close</span></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="field-group">
              <label className="field-label">Email address <span style={{color:'var(--red)'}}>*</span></label>
              <input className="field-input" type="email" required value={form.email} onChange={e => setForm({...form, email: e.target.value})} placeholder="admin@university.edu" />
            </div>
            <div className="field-group">
              <label className="field-label">Role</label>
              <select className="field-select" value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
                <option value="super_admin">Organization Admin</option>
              </select>
            </div>
            {form.role === 'super_admin' && (
              <div className="field-group">
                <label className="field-label">Organization <span style={{color:'var(--red)'}}>*</span></label>
                <select className="field-select" required value={form.org_id} onChange={e => setForm({...form, org_id: e.target.value})}>
                  <option value="">Select Organization</option>
                  {orgs.map(o => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" disabled={submitting || (form.role === 'super_admin' && !form.org_id)} className="btn btn-primary">
              <span className="material-symbols-outlined" style={{fontSize: '15px'}}>send</span> {submitting ? 'Sending...' : 'Send Invitation'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
