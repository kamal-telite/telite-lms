import { Button, Badge, IconButton } from "../../components/common/ui";
import { formatPercent, titleize } from "../../utils/formatters";

export default function FragmentCourseRow({
  course,
  expanded,
  onToggle,
  onEdit,
  onEditBuilder,
  onDelete,
  deleteOpen,
  onConfirmDelete,
  onCancelDelete,
}) {
  return (
    <>
      <tr>
        <td>
          <button type="button" className="panel-link" onClick={onToggle}>
            {course.name}
          </button>
          <div className="row-subtitle">{course.description}</div>
        </td>
        <td><Badge tone={course.tier === "Advanced" ? "accent" : "brand"}>{course.tier}</Badge></td>
        <td className="mono">{course.module_count} modules</td>
        <td className="mono">{course.enrolled_count}</td>
        <td className="mono">{formatPercent(course.completion_rate)}</td>
        <td><Badge tone={course.status === "active" ? "success" : "warn"}>{titleize(course.status)}</Badge></td>
        <td>
          <div className="split-actions">
            <Button tone="primary" size="small" onClick={onEditBuilder}>Edit in Builder</Button>
            <IconButton label="Edit course metadata" icon="pencil" onClick={onEdit} />
            <IconButton label="Delete course" icon="trash" onClick={onDelete} />
          </div>
        </td>
      </tr>
      {expanded ? (
        <tr>
          <td colSpan={7}>
            <div className="soft-card soft-card--tinted">
              <div className="row-title" style={{ marginBottom: 8 }}>Course structure preview</div>
              <div className="activity-list">
                {course.modules.map((module) => (
                  <div className="row-subtitle" key={module}>• {module}</div>
                ))}
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}
