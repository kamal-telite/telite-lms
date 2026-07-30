import { useState } from "react";
import { createPortal } from "react-dom";
import { useToast } from "../../components/common/ui";
import { platformApi } from "../../services/platform";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock";

export default function CreateOrganizationModal({ open, onClose, onCreated }) {
  const { showToast } = useToast();
  useBodyScrollLock(open);
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ name: "", type: "college", domain: "", slug: "", super_admin_email: "" });

  if (!open) return null;

  const canNext = (step === 1 && form.name.trim() && form.domain.trim()) || step === 2 || step === 3;

  return createPortal(
    <div className="overlay" onClick={onClose} style={{zIndex: 200}}>
      <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-title">Create New Organization</div>
            <div className="modal-sub">Set up a new educational or corporate partner.</div>
          </div>
          <button className="modal-close" onClick={onClose}><span className="material-symbols-outlined">close</span></button>
        </div>
        
        <div className="modal-body">
          <div className="stepper">
            <div className={`step ${step > 1 ? 'done' : step === 1 ? 'active' : 'pending'}`}>
              <div className="step-num">1</div><div className="step-label">Basic Info</div><div className="step-line"></div>
            </div>
            <div className={`step ${step > 2 ? 'done' : step === 2 ? 'active' : 'pending'}`}>
              <div className="step-num">2</div><div className="step-label">Admin Setup</div><div className="step-line"></div>
            </div>
            <div className={`step ${step === 3 ? 'active' : 'pending'}`}>
              <div className="step-num">3</div><div className="step-label">Review</div>
            </div>
          </div>

          {step === 1 && (
            <div>
              <div className="field-group">
                <label className="field-label">Organization Name <span style={{color: 'var(--red)'}}>*</span></label>
                <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="field-input" placeholder="e.g. Stanford University" type="text" />
              </div>
              <div className="field-row">
                <div className="field-group">
                  <label className="field-label">Organization Type <span style={{color: 'var(--red)'}}>*</span></label>
                  <select value={form.type} onChange={e => setForm({...form, type: e.target.value})} className="field-select">
                    <option value="college">College</option>
                    <option value="company">Company</option>
                  </select>
                </div>
                <div className="field-group">
                  <label className="field-label">Custom Domain <span style={{color: 'var(--red)'}}>*</span></label>
                  <input value={form.domain} onChange={e => setForm({...form, domain: e.target.value})} className="field-input" placeholder="e.g. stanford.edu" type="text" />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <div className="invite-hint">
                <span className="material-symbols-outlined" style={{fontSize: '15px', verticalAlign: 'middle'}}>info</span>
                If provided, an invitation link will be emailed to onboard via /set-password.
              </div>
              <div className="field-group">
                <label className="field-label">Super Admin Email (Optional)</label>
                <input value={form.super_admin_email} onChange={e => setForm({...form, super_admin_email: e.target.value})} className="field-input" placeholder="admin@example.edu" type="email" />
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <div className="invite-hint">
                <span className="material-symbols-outlined" style={{fontSize: '15px', verticalAlign: 'middle'}}>fact_check</span>
                TELITE will create the organization in the native platform. The super admin invitation is sent after creation when an email is provided.
              </div>
              <div className="field-group">
                <label className="field-label">Organization</label>
                <div style={{fontSize: '13px', fontWeight: 600}}>{form.name.trim() || 'N/A'}</div>
                <div style={{fontSize: '12px', color: 'var(--tx3)', marginTop: '3px'}}>
                  {form.type} - {form.domain.trim() || 'N/A'}
                </div>
              </div>
              <div className="field-group">
                <label className="field-label">Super Admin Invitation</label>
                <div style={{fontSize: '13px', fontWeight: 600}}>
                  {form.super_admin_email.trim() || 'No invitation email provided'}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {step > 1 && <button onClick={() => setStep(s=>s-1)} disabled={submitting} className="btn btn-secondary">Back</button>}
          <button onClick={onClose} disabled={submitting} className="btn btn-secondary">Cancel</button>
          
          {step < 3 ? (
            <button onClick={() => setStep(s=>s+1)} disabled={!canNext} className="btn btn-primary">Next Step</button>
          ) : (
            <button 
              disabled={submitting || !form.name.trim() || !form.domain.trim()} 
              onClick={async () => {
                setSubmitting(true);
                try {
                  await platformApi.createOrganization({
                    name: form.name.trim(), type: form.type, domain: form.domain.trim(),
                    slug: form.slug.trim() || null, super_admin_email: form.super_admin_email.trim() || null,
                  });
                  showToast("Organization created", "success");
                  onCreated?.();
                  onClose();
                } catch (err) {
                  showToast(err.response?.data?.detail || "Failed to create organization", "error");
                } finally {
                  setSubmitting(false);
                }
              }}
              className="btn btn-primary"
            >
              {submitting ? 'Creating...' : 'Create Organization'}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
