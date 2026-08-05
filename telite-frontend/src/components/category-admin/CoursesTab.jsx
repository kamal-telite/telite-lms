import { useState } from "react";
import { Panel, Button, Modal } from "../../components/common/ui";
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
  const [isDeleting, setIsDeleting] = useState(false);

  const confirmDelete = async () => {
    if (!deleteCourseId || isDeleting) return;
    setIsDeleting(true);
    try {
      await handleDeleteCourse(deleteCourseId);
    } finally {
      setIsDeleting(false);
    }
  };

  const courseToDelete = (dashboard?.courses || []).find(c => c.id === deleteCourseId);

  return (
    <>
      <Panel
        title="Course management"
        subtitle={`All ${dashboard?.category?.name || "category"} courses with structure preview`}
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
                  />
                ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Modal
        open={Boolean(deleteCourseId)}
        onClose={() => {
          if (!isDeleting) setDeleteCourseId(null);
        }}
        title="Archive Course"
        description="Are you sure you want to archive this course? Learners will no longer be able to access it."
        footer={
          <>
            <Button tone="ghost" onClick={() => setDeleteCourseId(null)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button tone="danger" onClick={confirmDelete} disabled={isDeleting}>
              {isDeleting ? "Archiving..." : "Archive Course"}
            </Button>
          </>
        }
      >
        <div className="soft-card soft-card--tinted">
          <div className="row-title">{courseToDelete?.name}</div>
          <div className="row-subtitle">
            {courseToDelete?.module_count || 0} modules • {courseToDelete?.enrolled_count || 0} enrolled
          </div>
        </div>
      </Modal>
    </>
  );
}
