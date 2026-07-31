import { Panel, Badge, Button } from "../../common/ui";

/**
 * ProfileSection - Learner profile information (Read-Only)
 */
export function ProfileSection({
  profile
}) {
  return (
    <section id="section-profile">
      <Panel
        title="Profile Information"
        subtitle="Your learner details"
        action={
          <Button tone="ghost" icon="edit" onClick={() => document.querySelector('[data-nav="section-settings"]')?.click()}>
            Edit Settings
          </Button>
        }
      >
        <div className="grid-2">
          <div className="soft-card">
            <div className="row-subtitle">Full Name</div>
            <div className="row-title">{profile.full_name}</div>
          </div>
          <div className="soft-card">
            <div className="row-subtitle">Email Address</div>
            <div className="row-title">{profile.email}</div>
          </div>
          <div className="soft-card">
            <div className="row-subtitle">Username</div>
            <div className="row-title">{profile.username}</div>
          </div>
          <div className="soft-card">
            <div className="row-subtitle">Organization</div>
            <div className="row-title">
              {profile.category_scope || "Telite Systems"}
            </div>
          </div>
          <div className="soft-card">
            <div className="row-subtitle">Enrollment Type</div>
            <div className="row-title">
              <Badge
                tone={
                  profile.enrollment_type === "self" ? "accent" : "brand"
                }
              >
                {profile.enrollment_type === "self"
                  ? "Self-Enrolled"
                  : "Organization Assigned"}
              </Badge>
            </div>
          </div>
          <div className="soft-card">
            <div className="row-subtitle">Learning Path Status</div>
            <div className="row-title">
              {profile.learning_path_active ? "Active" : "None Assigned"}
            </div>
          </div>
        </div>
      </Panel>
    </section>
  );
}
