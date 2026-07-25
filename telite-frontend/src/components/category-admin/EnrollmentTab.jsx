import { Panel, Button, Avatar } from "../../components/common/ui";
import { formatMonthDate, getInitials, titleize } from "../../utils/formatters";
import { getCourseEnrollmentDisabledReason, toggleEnrollmentCourseSelection } from "../../utils/enrollmentCourses";

export default function EnrollmentTab({ 
  dashboard, 
  labels, 
  handleApprove, 
  handleReject, 
  manualForm, 
  setManualForm, 
  manualErrors, 
  setManualErrors, 
  manualSuccess, 
  submitManualEnrollment 
}) {
  return (
    <div className="dashboard-stack">
      <Panel title="Pending requests" subtitle="All pending self-enrollment requests">
        <div className="activity-list">
          {(dashboard?.pending_enrollment || []).map((request) => (
            <div className="activity-item" key={request.id}>
              <Avatar initials={getInitials(request.full_name)} gradient={request.domain_verified ? ["#7C3AED", "#2563EB"] : ["#D97706", "#92400E"]} size={32} />
              <div style={{ flex: 1 }}>
                <div className="row-title">{request.full_name}</div>
                <div className="row-subtitle">{request.request_type} · {request.email}</div>
              </div>
              <div className="split-actions">
                <Button tone="success" onClick={() => handleApprove(request.id)}>Approve</Button>
                <Button tone="danger" onClick={() => handleReject(request.id)}>Deny</Button>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Manual Enrollment form" subtitle="Create learner access and enrol them into courses">
        {manualSuccess ? <div className="form-alert" style={{ background: "var(--emerald-light)", border: "1px solid var(--emerald-mid)", color: "var(--emerald)" }}>{manualSuccess}</div> : null}
        <form
          className="form-stack"
          onSubmit={async (event) => {
            event.preventDefault();
            const errors = {};
            if (!manualForm.full_name.trim()) errors.full_name = "Name is required.";
            if (!manualForm.email.trim()) errors.email = "Email is required.";
            if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(manualForm.email)) errors.email = "Enter a valid email address.";
            if (!manualForm.course_ids.length) errors.course_ids = "Select at least one course.";
            setManualErrors(errors);
            if (Object.keys(errors).length) return;
            await submitManualEnrollment(manualForm);
          }}
        >
          <div className="field-grid">
            <label className="field">
              <span className="field__label">{labels.user} name</span>
              <input className={`field__input ${manualErrors.full_name ? "is-invalid" : ""}`} value={manualForm.full_name} onChange={(event) => setManualForm((current) => ({ ...current, full_name: event.target.value }))} />
              {manualErrors.full_name ? <span className="field__error">{manualErrors.full_name}</span> : null}
            </label>
            <label className="field">
              <span className="field__label">Email address</span>
              <input className={`field__input ${manualErrors.email ? "is-invalid" : ""}`} value={manualForm.email} onChange={(event) => setManualForm((current) => ({ ...current, email: event.target.value }))} />
              {manualForm.email && !manualForm.email.endsWith("@telite.io") ? <span className="field__help">Warning: non-company domain, approval may be required.</span> : null}
              {manualErrors.email ? <span className="field__error">{manualErrors.email}</span> : null}
            </label>
          </div>
          <div className="field">
            <span className="field__label">Enrollment type</span>
            <div className="radio-row">
              {["manual", "self"].map((option) => (
                <label className="radio-pill" key={option}>
                  <input type="radio" checked={manualForm.enrollment_type === option} onChange={() => setManualForm((current) => ({ ...current, enrollment_type: option }))} />
                  {titleize(option === "self" ? "Self-enrollment" : option)}
                </label>
              ))}
            </div>
          </div>
          <div className="field">
            <span className="field__label">Courses to enroll in</span>
            <div className="checkbox-grid">
              {(dashboard?.courses || []).map((course) => {
                const disabledReason = getCourseEnrollmentDisabledReason(course);
                return (
                  <label className={`radio-pill ${disabledReason ? "is-disabled" : ""}`} key={course.id} title={disabledReason || undefined}>
                    <input
                      type="checkbox"
                      disabled={Boolean(disabledReason)}
                      checked={manualForm.course_ids.includes(course.id)}
                      onChange={() =>
                        setManualForm((current) => ({
                          ...current,
                          course_ids: toggleEnrollmentCourseSelection(current.course_ids, course),
                        }))
                      }
                    />
                    <span>{course.name}</span>
                    {disabledReason ? <span className="field__help">{disabledReason}</span> : null}
                  </label>
                );
              })}
            </div>
            {manualErrors.course_ids ? <span className="field__error">{manualErrors.course_ids}</span> : null}
          </div>
          <label className="field">
            <span className="field__label">Note / reason</span>
            <textarea className="field__textarea" value={manualForm.note} onChange={(event) => setManualForm((current) => ({ ...current, note: event.target.value }))} />
          </label>
          <Button tone="primary" type="submit" className="btn--block">Enroll {labels.user}</Button>
        </form>
      </Panel>
    </div>
  );
}
