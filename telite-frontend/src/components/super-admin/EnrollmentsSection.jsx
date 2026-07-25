import { Panel, Badge, Button, EmptyState, IconButton } from "../../components/common/ui";
import { getStatusTone } from "../../utils/formatters";

export default function EnrollmentsSection({ 
  dashboard, 
  isMoodleSource, 
  handleApprove, 
  handleReject,
  handleApproveAll,
  showToast 
}) {
  return (
    <section id="section-enrollments">
      <Panel
        title="Enrollment audit log"
        subtitle={isMoodleSource ? "Read-only" : "manual & self-enrol"}
        action={!isMoodleSource ? <button className="panel-link" type="button">View all</button> : null}
      >
        {isMoodleSource ? (
          <EmptyState
            title="Enrollment queue unavailable"
            body={dashboard.notes?.enrollment || "No enrollment queue returned from Moodle."}
          />
        ) : (
          <>
            <div id="section-enrollments" className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Category</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.enrollment_audit.rows.map((row) => (
                    <tr key={row.request_id}>
                      <td className="row-title">{row.full_name}</td>
                      <td className="muted">{row.category}</td>
                      <td>
                        <Badge tone={row.type === "self" ? "accent" : "brand"}>{row.type}</Badge>
                      </td>
                      <td>
                        <Badge tone={getStatusTone(row.status)}>{row.status}</Badge>
                      </td>
                      <td>
                        {row.status === "Pending" ? (
                          <div className="split-actions">
                            <Button tone="success" onClick={() => handleApprove(row.request_id)}>
                              Approve
                            </Button>
                            <Button tone="danger" onClick={() => handleReject(row.request_id)}>
                              Deny
                            </Button>
                          </div>
                        ) : (
                          <IconButton
                            label="View request"
                            icon="eye"
                            onClick={() => showToast(`Viewing ${row.full_name} enrollment history.`, "info")}
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="split-actions">
              <Button
                tone="ghost"
                onClick={handleApproveAll}
                disabled={!dashboard.enrollment_audit.visible_pending_ids.length}
              >
                Approve pending ({dashboard.enrollment_audit.visible_pending_ids.length})
              </Button>
              <Button tone="ghost" onClick={() => showToast("Enrollment log export initiated...", "info")}>
                Export CSV
              </Button>
            </div>
          </>
        )}
      </Panel>
    </section>
  );
}
