import { Panel, Badge, EmptyState, Button } from "../../components/common/ui";
import { formatDateTime, titleize } from "../../utils/formatters";

export default function AuditSection({ 
  dashboard, 
  isMoodleSource, 
  visibleAudit, 
  expandedAudit, 
  setExpandedAudit 
}) {
  return (
    <section id="section-audit">
      <Panel
        title="Audit log"
        subtitle="Recent system activity"
        action={
          !isMoodleSource && visibleAudit.length ? (
            <button className="panel-link" type="button" onClick={() => setExpandedAudit((value) => !value)}>
              {expandedAudit ? "Collapse" : "Full log"}
            </button>
          ) : null
        }
      >
        <div className="search-toolbar" style={{ marginBottom: 16 }}>
          <div className="toolbar">
            <label className="chip">
              <input type="radio" defaultChecked name="auditFilter" /> All
            </label>
            <label className="chip">
              <input type="radio" name="auditFilter" /> Login
            </label>
            <label className="chip">
              <input type="radio" name="auditFilter" /> Enrollment
            </label>
            <label className="chip">
              <input type="radio" name="auditFilter" /> Verification
            </label>
          </div>
          <label className="field" style={{ flex: 1, maxWidth: 300 }}>
            <input className="field__input" type="text" placeholder="Search users or actions..." />
          </label>
        </div>

        {visibleAudit.length ? (
          <div id="section-audit" className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Details</th>
                  <th>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {visibleAudit.map((entry) => (
                  <tr key={entry.id}>
                    <td className="mono" style={{ whiteSpace: "nowrap" }}>
                      {formatDateTime(entry.created_at)}
                    </td>
                    <td>
                      <div className="row-title">{entry.actor_name}</div>
                    </td>
                    <td>
                      <Badge tone={entry.accent === "amber" ? "warn" : entry.accent === "blue" ? "brand" : "neutral"}>
                        {titleize(entry.accent || "system")}
                      </Badge>
                    </td>
                    <td>
                      <div className="row-subtitle" style={{ color: "var(--text-primary)" }}>{entry.message}</div>
                      <div className="row-subtitle muted">{entry.result}</div>
                    </td>
                    <td className="mono">{entry.ip_address || "192.168.1.1"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Audit log unavailable" body={dashboard.notes?.audit || "No audit data available."} />
        )}
        {!isMoodleSource && visibleAudit.length ? (
          <div style={{ marginTop: 16 }}>
            <Button tone="ghost" className="btn--block" onClick={() => setExpandedAudit((value) => !value)}>
              {expandedAudit ? "Hide extra entries" : "Load more entries"}
            </Button>
          </div>
        ) : null}
      </Panel>
    </section>
  );
}
