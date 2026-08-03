import { Panel, Button } from "../../components/common/ui";
import FragmentCourseRow from "./FragmentCourseRow";

export default function CoursesTab({ 
  dashboard, 
  courseSearch, 
  setCourseSearch, 
  setCourseModal, 
  expandedCourseId, 
  setExpandedCourseId, 
  setDeleteCourseId, 
  deleteCourseId, 
  handleDeleteCourse, 
  navigate,
  slug
}) {
  return (
    <Panel
      title="Course management"
      subtitle={`All ${dashboard.category?.name || "category"} courses with structure preview`}
      action={
        <div className="split-actions">
          <input
            className="field__input"
            placeholder="Search courses..."
            value={courseSearch}
            onChange={(event) => setCourseSearch(event.target.value)}
          />
          <Button tone="primary" onClick={() => setCourseModal({ open: true, item: null })}>+ New course</Button>
        </div>
      }
    >
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Course</th>
              <th>Tier</th>
              <th>Modules</th>
              <th>Enrolled</th>
              <th>Completion</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {(dashboard?.courses || [])
              .filter((course) => course.name.toLowerCase().includes(courseSearch.toLowerCase()))
              .map((course) => (
                <FragmentCourseRow
                  key={course.id}
                  course={course}
                  expanded={expandedCourseId === course.id}
                  onToggle={() => setExpandedCourseId((value) => (value === course.id ? null : course.id))}
                  onEdit={() => setCourseModal({ open: true, item: course })}
                  onEditBuilder={() => navigate(`/categories/${slug}/builder/${course.id}`)}
                  onDelete={() => setDeleteCourseId((value) => (value === course.id ? null : course.id))}
                  deleteOpen={deleteCourseId === course.id}
                  onConfirmDelete={() => handleDeleteCourse(course.id)}
                  onCancelDelete={() => setDeleteCourseId(null)}
                />
              ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
