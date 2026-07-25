import { Button, Panel, Badge } from "../../common/ui";

/**
 * ProfileSection - Learner profile information and editing
 */
export function ProfileSection({
  profile,
  isEditing,
  profileForm,
  onFormChange,
  onEditStart,
  onEditCancel,
  onSave,
}) {
  return (
    <section id="section-profile">
      <Panel
        title="Profile Information"
        subtitle="Your learner details"
        action={
          isEditing ? (
            <div className="split-actions">
              <Button tone="ghost" onClick={onEditCancel}>
                Cancel
              </Button>
              <Button tone="primary" onClick={onSave}>
                Save Changes
              </Button>
            </div>
          ) : (
            <Button tone="ghost" icon="edit" onClick={onEditStart}>
              Edit Profile
            </Button>
          )
        }
      >
        <div className="grid-2">
          <div className="soft-card">
            <div className="row-subtitle">Full Name</div>
            {isEditing ? (
              <input
                className="field__input"
                style={{ marginTop: 8 }}
                value={profileForm.full_name}
                onChange={(e) =>
                  onFormChange({ ...profileForm, full_name: e.target.value })
                }
              />
            ) : (
              <div className="row-title">{profile.full_name}</div>
            )}
          </div>
          <div className="soft-card">
            <div className="row-subtitle">Email Address</div>
            {isEditing ? (
              <input
                className="field__input"
                style={{ marginTop: 8 }}
                type="email"
                value={profileForm.email}
                onChange={(e) =>
                  onFormChange({ ...profileForm, email: e.target.value })
                }
              />
            ) : (
              <div className="row-title">{profile.email}</div>
            )}
          </div>
          <div className="soft-card">
            <div className="row-subtitle">Organization</div>
            {isEditing ? (
              <select
                className="field__select"
                style={{ marginTop: 8 }}
                value={profileForm.organization_id}
                onChange={(e) =>
                  onFormChange({
                    ...profileForm,
                    organization_id: e.target.value,
                  })
                }
              >
                <option value="1">Telite Systems (HQ)</option>
                <option value="2">Acme Corp</option>
                <option value="3">Globex Inc</option>
              </select>
            ) : (
              <div className="row-title">
                {profile.category_scope || "Telite Systems"}
              </div>
            )}
          </div>
          <div className="soft-card">
            <div className="row-subtitle">Enrollment Type</div>
            <div className="row-title" style={{ marginTop: isEditing ? 8 : 0 }}>
              <Badge
                tone={
                  profile.enrollment_type === "self" ? "accent" : "brand"
                }
              >
                {profile.enrollment_type}
              </Badge>
            </div>
          </div>
        </div>
      </Panel>
    </section>
  );
}
