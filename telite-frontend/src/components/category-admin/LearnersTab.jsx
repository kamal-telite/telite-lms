import { Panel, Button, Avatar, Badge, IconButton } from "../../components/common/ui";
import { formatShortDate, formatPercent, getScoreColor, getInitials } from "../../utils/formatters";

export default function LearnersTab({ 
  labels, 
  learnerSearch, 
  setLearnerSearch, 
  learnerFilter, 
  setLearnerFilter, 
  setLearnerModal, 
  paginatedLearners, 
  learnerPage, 
  pageCount, 
  setLearnerPage, 
  setDetailLearner, 
  setDeleteLearnerId, 
  deleteLearnerId, 
  handleDeleteLearner,
  dashboard
}) {
  return (
    <div className="tab-stack">
      <Panel
        title={`Manage ${labels.users}`}
        subtitle={`Overview of ${labels.users.toLowerCase()} enrolled in ${dashboard.category?.name}`}
        action={
          <div className="toolbar">
            <input
              className="field__input"
              placeholder={`Search by name or email...`}
              value={learnerSearch}
              onChange={(event) => setLearnerSearch(event.target.value)}
            />
            <select className="field__select" value={learnerFilter} onChange={(event) => setLearnerFilter(event.target.value)}>
              <option value="all">All</option>
              <option value="manual">Manual</option>
              <option value="self">Self-enrolled</option>
            </select>
            <Button tone="primary" onClick={() => setLearnerModal({ open: true, seed: null })}>+ Add {labels.user}</Button>
          </div>
        }
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{labels.user}</th>
                <th>Enrolled date</th>
                <th>Courses</th>
                <th>PAL Score</th>
                <th>Enrollment type</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedLearners.map((learner) => (
                <tr key={learner.id}>
                  <td>
                    <div className="leaderboard-row" style={{ padding: 0, borderBottom: 0 }}>
                      <Avatar initials={learner.avatar_initials || getInitials(learner.full_name)} gradient={learner.avatar_gradient} size={26} />
                      <div>
                        <div className="row-title">{learner.full_name}</div>
                        <div className="row-subtitle">{learner.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="mono">{formatShortDate(learner.created_at)}</td>
                  <td className="mono">{learner.courses_completed}/{learner.total_courses}</td>
                  <td className="mono" style={{ color: getScoreColor(learner.pal_score) }}>{formatPercent(learner.pal_score)}</td>
                  <td><Badge tone={learner.enrollment_type === "self" ? "accent" : "brand"}>{learner.enrollment_type}</Badge></td>
                  <td><Badge tone={learner.is_active ? "success" : "neutral"}>{learner.is_active ? "Active" : "Inactive"}</Badge></td>
                  <td>
                    <div className="split-actions">
                      <IconButton label="View learner" icon="eye" onClick={() => setDetailLearner(learner)} />
                      {learner.enrollment_type === "self" ? (
                        <IconButton label="Delete learner" icon="trash" onClick={() => setDeleteLearnerId((value) => (value === learner.id ? null : learner.id))} />
                      ) : null}
                    </div>
                    {deleteLearnerId === learner.id ? (
                      <div className="inline-confirm">
                        <span>Remove this {labels.user.toLowerCase()}?</span>
                        <div className="split-actions">
                          <Button tone="danger" onClick={() => handleDeleteLearner(learner.id)}>Confirm delete</Button>
                          <Button tone="ghost" onClick={() => setDeleteLearnerId(null)}>Cancel</Button>
                        </div>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pagination" style={{ marginTop: 16 }}>
          <Button tone="ghost" disabled={learnerPage === 1} onClick={() => setLearnerPage(1)}>Page 1</Button>
          <Button tone="ghost" disabled={learnerPage === pageCount} onClick={() => setLearnerPage((prev) => Math.min(prev + 1, pageCount))}>Next</Button>
        </div>
      </Panel>
    </div>
  );
}
