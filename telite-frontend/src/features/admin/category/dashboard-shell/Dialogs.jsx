import React, { Component, useEffect, useState } from "react";
import { Badge, Button, Modal, StatCard } from "../../../../components/common/ui";
import { deleteCourseCover } from "../../../../services/client";
import { formatShortDate, titleize } from "../../../../utils/formatters";
import { getCourseEnrollmentDisabledReason, toggleEnrollmentCourseSelection } from "../../../../utils/enrollmentCourses";
import { COURSE_INITIAL, LEARNER_INITIAL, TASK_INITIAL } from "./constants";

function CourseEditorModal({ open, item, onClose, onSubmit, onOpenBuilder }) {
  const isEdit = Boolean(item);
  const [form, setForm] = useState(COURSE_INITIAL);
  const [errors, setErrors] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadError, setUploadError] = useState("");

  useEffect(() => {
    setForm(
      item
        ? {
            name: item.name,
            slug: item.slug,
            description: item.description,
            tier: item.tier,
            status: item.status,
            cover_image_url: item.cover_image_url || "",
          }
        : COURSE_INITIAL
    );
    setSelectedFile(null);
    setUploadError("");
    setErrors({});
  }, [item, open]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const ext = file.name.split('.').pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      setUploadError("Invalid format. Only JPG, JPEG, PNG, and WEBP are supported.");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setUploadError("File is too large. Maximum size is 5 MB.");
      return;
    }

    setUploadError("");
    setSelectedFile(file);
  };

  const handleRemoveImage = async () => {
    setSelectedFile(null);
    setUploadError("");
    if (isEdit && form.cover_image_url) {
      try {
        await deleteCourseCover(item.category_slug || item.slug, item.id);
        updateField("cover_image_url", "");
      } catch {
        setUploadError("Failed to remove cover image.");
      }
    }
  };

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!form.name.trim()) nextErrors.name = "Course name is required.";
    if (!form.description.trim()) nextErrors.description = "Description is required.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }
    try {
      await onSubmit(
        {
          name: form.name,
          slug: form.slug || form.name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
          description: form.description,
          tier: form.tier,
          status: form.status,
          cover_image_url: form.cover_image_url,
        },
        isEdit,
        selectedFile
      );
    } catch (err) {
      if (err.response?.status === 409 && err.response?.data?.detail) {
        const d = err.response.data.detail;
        if (d.field) {
          setErrors({ [d.field]: d.message });
        } else {
          setErrors({ name: d.message || "A conflict occurred." });
        }
      }
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Course Settings" : "Create New Course"}
      description={isEdit ? "Manage metadata and structure." : "Initialize a new course shell."}
      width={640}
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>Cancel</Button>
          <Button tone="primary" type="submit" form="course-editor-form">{isEdit ? "Save Changes" : "Create Course"}</Button>
        </>
      }
    >
      <form id="course-editor-form" onSubmit={handleSubmit}>
        <div className="form-section">
          <h3 className="form-section__title">1. Basic Information</h3>
          <div className="form-stack">
            <label className="field">
              <span className="field__label">Course Name</span>
              <input className={`field__input ${errors.name ? "is-invalid" : ""}`} value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="e.g. Introduction to Python" />
              {errors.name ? <span className="field__error">{errors.name}</span> : null}
            </label>
            <label className="field">
              <span className="field__label">Description</span>
              <input className={`field__input ${errors.description ? "is-invalid" : ""}`} value={form.description} onChange={(event) => updateField("description", event.target.value)} placeholder="Short summary of the course..." />
              {errors.description ? <span className="field__error">{errors.description}</span> : null}
            </label>

            <div className="field">
              <span className="field__label">Course Cover Image</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', border: '1px dashed var(--border)', borderRadius: '6px', padding: '12px', background: 'var(--surface-raised)' }}>
                {(form.cover_image_url || selectedFile) && (
                  <div style={{ position: 'relative', width: '200px', height: '112.5px', borderRadius: '4px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                    <img
                      src={selectedFile ? URL.createObjectURL(selectedFile) : form.cover_image_url}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      alt="Cover Preview"
                    />
                  </div>
                )}
                
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <label className="button button--small button--secondary" style={{ cursor: 'pointer', display: 'inline-flex', margin: 0 }}>
                    {form.cover_image_url || selectedFile ? "Replace Image" : "Upload Image"}
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png,.webp"
                      style={{ display: 'none' }}
                      onChange={handleFileChange}
                    />
                  </label>
                  
                  {(form.cover_image_url || selectedFile) && (
                    <Button tone="ghost" size="small" onClick={handleRemoveImage}>
                      Remove
                    </Button>
                  )}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Recommended: 1280 × 720 (16:9) • Max: 5 MB • Formats: JPG, JPEG, PNG, WEBP
                </div>
                {uploadError && <span className="field__error">{uploadError}</span>}
              </div>
            </div>

            <div className="field-grid">
              <label className="field">
                <span className="field__label">Tier</span>
                <select className="field__select" value={form.tier} onChange={(event) => updateField("tier", event.target.value)}>
                  <option value="Basic">Basic</option>
                  <option value="Advanced">Advanced</option>
                </select>
              </label>
              <label className="field">
                <span className="field__label">Status</span>
                <select className="field__select" value={form.status} onChange={(event) => updateField("status", event.target.value)}>
                  <option value="active">Active</option>
                  <option value="draft">Draft</option>
                </select>
              </label>
            </div>
          </div>
        </div>

        {isEdit && (
          <>
            <div className="form-section">
              <h3 className="form-section__title">2. Course Statistics</h3>
              <div className="grid-4">
                <div>
                  <StatCard label="Modules" value={item?.module_count || 0} />
                </div>
                <div>
                  <StatCard label="Lessons" value={item?.lessons_count || 0} />
                </div>
                <div>
                  <StatCard label="Blocks" value={item?.blocks_count || 0} />
                </div>
                <div>
                  <StatCard label="Enrollments" value={item?.enrolled_count || 0} />
                </div>
              </div>
            </div>

            <div className="form-section">
              <h3 className="form-section__title">3. Builder Access</h3>
              <div className="soft-card soft-card--tinted" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div className="row-title">Course Builder</div>
                  <div className="row-subtitle">Manage modules, lessons, and interactive blocks.</div>
                </div>
                <Button tone="primary" type="button" onClick={() => onOpenBuilder(item.id)}>Open Course Builder</Button>
              </div>
            </div>

            <div className="form-section">
              <h3 className="form-section__title">4. Metadata</h3>
              <div className="grid-3" style={{ fontSize: "13px" }}>
                <div>
                  <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Created Date</div>
                  <div className="mono">{item?.created_at ? formatShortDate(item.created_at) : "Just now"}</div>
                </div>
                <div>
                  <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Updated Date</div>
                  <div className="mono">{item?.updated_at ? formatShortDate(item.updated_at) : "Just now"}</div>
                </div>
                <div>
                  <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Publish Status</div>
                  <div><Badge tone={item?.status === "active" ? "success" : "neutral"}>{titleize(item?.status || "draft")}</Badge></div>
                </div>
              </div>
            </div>
          </>
        )}
      </form>
    </Modal>
  );
}

function LearnerEditorModal({ open, seed, courses, onClose, onSubmit }) {
  const [form, setForm] = useState(LEARNER_INITIAL);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setForm({ ...LEARNER_INITIAL, ...seed });
    setErrors({});
  }, [seed, open]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!form.full_name.trim()) nextErrors.full_name = "Full name is required.";
    if (!form.email.trim()) nextErrors.email = "Email is required.";
    if (!form.course_ids.length) nextErrors.course_ids = "Select at least one course.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }
    await onSubmit(form);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add Learner"
      description="Create a learner account and assign ATS courses."
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>Cancel</Button>
          <Button tone="primary" type="submit" form="learner-editor-form">Add Learner</Button>
        </>
      }
    >
      <form id="learner-editor-form" className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Full name</span>
          <input className={`field__input ${errors.full_name ? "is-invalid" : ""}`} value={form.full_name} onChange={(event) => updateField("full_name", event.target.value)} />
          {errors.full_name ? <span className="field__error">{errors.full_name}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Email</span>
          <input className={`field__input ${errors.email ? "is-invalid" : ""}`} value={form.email} onChange={(event) => updateField("email", event.target.value)} />
          {errors.email ? <span className="field__error">{errors.email}</span> : null}
        </label>
        <div className="field">
          <span className="field__label">Enrollment type</span>
          <div className="radio-row">
            {["manual", "self"].map((option) => (
              <label className="radio-pill" key={option}>
                <input type="radio" checked={form.enrollment_type === option} onChange={() => updateField("enrollment_type", option)} />
                {titleize(option)}
              </label>
            ))}
          </div>
        </div>
        <div className="field">
          <span className="field__label">Courses</span>
          <div className="checkbox-grid">
            {courses.map((course) => {
              const disabledReason = getCourseEnrollmentDisabledReason(course);
              return (
                <label className={`radio-pill ${disabledReason ? "is-disabled" : ""}`} key={course.id} title={disabledReason || undefined}>
                  <input
                    type="checkbox"
                    disabled={Boolean(disabledReason)}
                    checked={form.course_ids.includes(course.id)}
                    onChange={() =>
                      updateField(
                        "course_ids",
                        toggleEnrollmentCourseSelection(form.course_ids, course)
                      )
                    }
                  />
                  <span>{course.name}</span>
                  {disabledReason ? <span className="field__help">{disabledReason}</span> : null}
                </label>
              );
            })}
          </div>
          {errors.course_ids ? <span className="field__error">{errors.course_ids}</span> : null}
        </div>
        <label className="field">
          <span className="field__label">Note</span>
          <textarea className="field__textarea" value={form.note} onChange={(event) => updateField("note", event.target.value)} />
        </label>
      </form>
    </Modal>
  );
}

function TaskAssignModal({ open, item, learners, onClose, onSubmit, categorySlug }) {
  const isEdit = Boolean(item);
  const [form, setForm] = useState(TASK_INITIAL);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setForm(
      item
        ? {
            title: item.title,
            description: item.description,
            assigned_to_user_id: item.assigned_to_user_id || "all",
            due_at: item.due_at,
            notes: item.notes || "",
          }
        : TASK_INITIAL
    );
    setErrors({});
  }, [item, open]);

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!form.title.trim()) nextErrors.title = "Task title is required.";
    if (!form.due_at) nextErrors.due_at = "Due date is required.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }
    const learner = learners.find((entry) => entry.id === form.assigned_to_user_id);
    await onSubmit(
      {
        title: form.title,
        description: form.description,
        assigned_label: learner?.full_name || "All learners",
        assigned_to_user_id: learner?.id || null,
        assignment_scope: learner ? "individual" : "all_learners",
        category_slug: categorySlug,
        due_at: form.due_at,
        status: item?.status || "pending",
        notes: form.notes,
        is_cross_category: false,
      },
      isEdit
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Assign Task"
      description="Assign a practice task to an individual learner or the full cohort."
      footer={
        <>
          <Button tone="ghost" onClick={onClose}>Cancel</Button>
          <Button tone="primary" type="submit" form="task-editor-form">{isEdit ? "Save changes" : "Assign Task"}</Button>
        </>
      }
    >
      <form id="task-editor-form" className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Task title</span>
          <input className={`field__input ${errors.title ? "is-invalid" : ""}`} value={form.title} onChange={(event) => { setForm((current) => ({ ...current, title: event.target.value })); setErrors((current) => ({ ...current, title: "" })); }} />
          {errors.title ? <span className="field__error">{errors.title}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Assign to</span>
          <select className="field__select" value={form.assigned_to_user_id} onChange={(event) => setForm((current) => ({ ...current, assigned_to_user_id: event.target.value }))}>
            <option value="all">All learners</option>
            {learners.map((learner) => (
              <option key={learner.id} value={learner.id}>{learner.full_name}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Due date</span>
          <input className={`field__input ${errors.due_at ? "is-invalid" : ""}`} type="date" value={form.due_at} onChange={(event) => { setForm((current) => ({ ...current, due_at: event.target.value })); setErrors((current) => ({ ...current, due_at: "" })); }} />
          {errors.due_at ? <span className="field__error">{errors.due_at}</span> : null}
        </label>
        <label className="field">
          <span className="field__label">Additional notes (optional)</span>
          <textarea className="field__textarea" value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
        </label>
      </form>
    </Modal>
  );
}



class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(_error) {
    return { hasError: true };
  }
  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "2rem", color: "var(--danger)", textAlign: "center" }}>
          <h2>Something went wrong loading this dashboard.</h2>
          <p>Please refresh the page or try again later.</p>
        </div>
      );
    }
    return this.props.children;
  }
}



export { CourseEditorModal, LearnerEditorModal, TaskAssignModal, ErrorBoundary };
