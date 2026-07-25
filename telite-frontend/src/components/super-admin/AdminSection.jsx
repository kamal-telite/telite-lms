import { Panel, Avatar, Badge, IconButton, EmptyState, Button } from "../../components/common/ui";
import { getRoleLabel } from "../../utils/formatters";

export default function AdminSection({ 
  dashboard, 
  isMoodleSource, 
  setAdminModal 
}) {
  return (
    <section id="section-admin">
      <Panel
        title="Admin control"
        subtitle={
          isMoodleSource
            ? "Read-only admin roles mapped from live Moodle accounts"
            : "Assigned category administrators"
        }
        action={
          <button className="panel-link" type="button" onClick={() => setAdminModal({ open: true, item: null })}>
            + Invite admin
          </button>
        }
      >
        <div id="section-admin">
          {dashboard.admins.length ? (
            dashboard.admins.map((admin) => (
              <div className="admin-row" key={admin.id}>
                <Avatar initials={admin.avatar_initials} gradient={admin.avatar_gradient} size={30} />
                <div style={{ flex: 1 }}>
                  <div className="row-title">{admin.full_name}</div>
                  <div className="row-subtitle">{admin.email}</div>
                </div>
                <Badge tone={admin.role === "super_admin" ? "accent" : "brand"}>
                  {getRoleLabel(admin)}
                </Badge>
                <IconButton
                  label="Edit admin"
                  icon="pencil"
                  onClick={() => setAdminModal({ open: true, item: admin })}
                />
              </div>
            ))
          ) : (
            <EmptyState title="No synced admins found" body={dashboard.notes?.admins || "No admin data available."} />
          )}
        </div>
        <div style={{ marginTop: 16 }}>
          {isMoodleSource ? (
            <div className="field__help">{dashboard.notes?.admins}</div>
          ) : (
            <Button
              tone="ghost"
              className="btn--block"
              onClick={() => document.getElementById("section-users")?.scrollIntoView({ behavior: "smooth" })}
            >
              Manage all admins
            </Button>
          )}
        </div>
      </Panel>
    </section>
  );
}
