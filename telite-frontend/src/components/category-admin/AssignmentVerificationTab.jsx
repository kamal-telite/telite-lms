import { StatCard, Panel, Button, LoadingState, EmptyState, Badge } from "../../components/common/ui";
import { formatDateTime, formatDuration, titleize, formatPercent } from "../../utils/formatters";

export default function AssignmentVerificationTab({ 
  assignmentQueue, 
  assignmentLoading, 
  assignmentFilters, 
  setAssignmentFilters, 
  loadAssignmentQueue, 
  handleAssignmentReview, 
  handleAssignmentDownload, 
  reviewDrafts, 
  setReviewDrafts,
  dashboard 
}) {
  return (
    <div className="dashboard-stack">
      <div className="grid-4">
        <StatCard accent="#D97706" label="Pending Assignments" value={assignmentQueue?.stats?.pending || 0} meta="Awaiting review" />
        <StatCard accent="#059669" label="Approved Assignments" value={assignmentQueue?.stats?.approved || 0} meta="Verified" />
        <StatCard accent="#DC2626" label="Rejected Assignments" value={assignmentQueue?.stats?.rejected || 0} meta="Needs learner action" />
        <StatCard accent="#2563EB" label="Total Submitted" value={assignmentQueue?.stats?.total || 0} meta="All statuses" />
      </div>

      <Panel title="Assignment Verification" subtitle="Review learner submissions across this category">
        <div className="toolbar" style={{ marginBottom: 16 }}>
          <label className="field" style={{ minWidth: 180 }}>
            <span className="field__label">Status</span>
            <select className="field__input" value={assignmentFilters.status} onChange={(event) => setAssignmentFilters((current) => ({ ...current, status: event.target.value }))}>
              <option value="">All statuses</option>
              <option value="pending_verification">Pending Verification</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
          <label className="field" style={{ minWidth: 220 }}>
            <span className="field__label">Course</span>
            <select className="field__input" value={assignmentFilters.course_id} onChange={(event) => setAssignmentFilters((current) => ({ ...current, course_id: event.target.value }))}>
              <option value="">All courses</option>
              {(dashboard?.courses || []).map((course) => (
                <option key={course.id} value={course.id}>{course.name}</option>
              ))}
            </select>
          </label>
          <label className="field" style={{ flex: 1, minWidth: 240 }}>
            <span className="field__label">Search</span>
            <input className="field__input" value={assignmentFilters.search} onChange={(event) => setAssignmentFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Learner or course" />
          </label>
          <label className="field">
            <span className="field__label">&nbsp;</span>
            <Button tone="ghost" onClick={loadAssignmentQueue} disabled={assignmentLoading}>{assignmentLoading ? "Loading..." : "Refresh"}</Button>
          </label>
          {/* <Button tone="ghost" onClick={loadAssignmentQueue} disabled={assignmentLoading}>{assignmentLoading ? "Loading..." : "Refresh"}</Button> */}
        </div>

        {assignmentLoading ? (
          <LoadingState title="Loading submissions..." body="Fetching assignments awaiting verification." />
        ) : (assignmentQueue?.submissions || []).length === 0 ? (
          <EmptyState title="No submissions found" body="Assignments matching these filters will appear here." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Learner</th>
                  <th>Course</th>
                  <th>Assignment</th>
                  <th>Submitted</th>
                  <th>Status</th>
                  <th>Attempt</th>
                  <th>Time</th>
                  <th>Progress</th>
                  <th>File</th>
                  <th>Review</th>
                </tr>
              </thead>
              <tbody>
                {(assignmentQueue?.submissions || []).map((submission) => {
                  const files = submission.files || submission.submission_files_json || [];
                  const firstFile = files[0];
                  const isPending = ["submitted", "resubmitted", "pending_verification"].includes(submission.status);
                  return (
                    <tr key={submission.id}>
                      <td>
                        <div className="row-title">{submission.learner?.name}</div>
                        <div className="row-subtitle">{submission.learner?.email}</div>
                      </td>
                      <td>
                        <div className="row-title">{submission.course?.name}</div>
                        <div className="row-subtitle">{submission.course?.category_slug}</div>
                      </td>
                      <td>{submission.assignment_name}</td>
                      <td className="mono">{formatDateTime(submission.submitted_at)}</td>
                      <td><Badge tone={submission.status === "approved" ? "success" : submission.status === "rejected" ? "danger" : "warn"}>{titleize(String(submission.status).replace("_", " "))}</Badge></td>
                      <td className="mono">{submission.attempt_number || 1}</td>
                      <td className="mono">{formatDuration(submission.time_spent_seconds || submission.course_time_seconds_at_submission || 0)}</td>
                      <td className="mono">{formatPercent(submission.course_progress || submission.course_progress_pct_at_submission || 0)}</td>
                      <td>
                        {files.length ? (
                          <button
                            type="button"
                            className="link-button"
                            onClick={(event) => handleAssignmentDownload(event, submission, firstFile)}
                          >
                            View/Download
                          </button>
                        ) : <span className="muted">No file</span>}
                      </td>
                      <td style={{ minWidth: 240 }}>
                        <textarea
                          className="field__input"
                          rows={2}
                          disabled={!isPending}
                          value={reviewDrafts[submission.id] ?? submission.feedback ?? ""}
                          onChange={(event) => setReviewDrafts((current) => ({ ...current, [submission.id]: event.target.value }))}
                          placeholder="Feedback or remarks"
                        />
                        <div className="split-actions" style={{ marginTop: 8 }}>
                          <Button tone="success" disabled={!isPending} onClick={() => handleAssignmentReview(submission.id, "approve")}>Approve</Button>
                          <Button tone="danger" disabled={!isPending} onClick={() => handleAssignmentReview(submission.id, "reject")}>Reject</Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
