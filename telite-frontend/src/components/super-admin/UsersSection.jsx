import { Panel, Avatar, Badge, IconButton, EmptyState, Button } from "../../components/common/ui";
import { formatPercent, getInitials, getRoleLabel } from "../../utils/formatters";

export default function UsersSection({ 
  users, 
  isMoodleSource, 
  userFilter, 
  setUserFilter, 
  userQuery, 
  setUserQuery, 
  filteredUsers, 
  setUserDeleteId, 
  userDeleteId, 
  handleDeleteUser,
  showToast 
}) {
  return (
    <section id="section-users">
      <Panel
        title="All users"
        subtitle={
          isMoodleSource
            ? `${users.length} live Moodle accounts`
            : `${users.length} accounts across admins and learners`
        }
        action={
          <div className="toolbar">
            <label className="chip">
              <input
                type="radio"
                checked={userFilter === "all"}
                onChange={() => setUserFilter("all")}
              />
              All
            </label>
            <label className="chip">
              <input
                type="radio"
                checked={userFilter === "admins"}
                onChange={() => setUserFilter("admins")}
              />
              Admins
            </label>
            <label className="chip">
              <input
                type="radio"
                checked={userFilter === "learners"}
                onChange={() => setUserFilter("learners")}
              />
              Learners
            </label>
          </div>
        }
      >
        <div className="search-toolbar" style={{ marginBottom: 16 }}>
          <label className="field" style={{ flex: 1 }}>
            <span className="field__label">{isMoodleSource ? "Search Moodle users" : "Search users"}</span>
            <input
              className="field__input"
              type="text"
              value={userQuery}
              onChange={(event) => setUserQuery(event.target.value)}
              placeholder="Search by name, email, or username..."
            />
          </label>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Category</th>
                <th>PAL</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td>
                    <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                      <Avatar
                        initials={user.avatar_initials || getInitials(user.full_name)}
                        gradient={user.avatar_gradient || ["#2563EB", "#7C3AED"]}
                        size={28}
                      />
                      <div>
                        <div className="row-title">{user.full_name}</div>
                        <div className="row-subtitle">{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <Badge
                      tone={
                        user.role === "super_admin"
                          ? "accent"
                          : user.role === "category_admin"
                            ? "brand"
                            : "neutral"
                      }
                    >
                      {getRoleLabel(user)}
                    </Badge>
                  </td>
                  <td className="muted">{user.category_scope || "Global"}</td>
                  <td className="mono">{user.role === "learner" ? formatPercent(user.pal_score) : "--"}</td>
                  <td>
                    <Badge tone={user.is_active ? "success" : "neutral"}>
                      {user.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td>
                    <div className="split-actions">
                      <IconButton
                        label="View user"
                        icon="eye"
                        onClick={() => showToast(`Viewing ${user.full_name}.`, "info")}
                      />
                      {!isMoodleSource ? (
                        <IconButton
                          label="Archive user"
                          icon="trash"
                          onClick={() => setUserDeleteId((value) => (value === user.id ? null : user.id))}
                        />
                      ) : null}
                    </div>
                    {!isMoodleSource && userDeleteId === user.id ? (
                      <div className="inline-confirm">
                        <span>Archive {user.full_name}?</span>
                        <div className="split-actions">
                          <Button tone="danger" onClick={() => handleDeleteUser(user.id)}>
                            Confirm delete
                          </Button>
                          <Button tone="ghost" onClick={() => setUserDeleteId(null)}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filteredUsers.length ? (
            <EmptyState title="No users found" body="Try a different role filter or search term." />
          ) : null}
        </div>
      </Panel>
    </section>
  );
}
