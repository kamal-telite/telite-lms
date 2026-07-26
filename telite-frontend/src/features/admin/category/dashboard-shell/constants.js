export const COURSE_INITIAL = {
  name: "",
  slug: "",
  description: "",
  tier: "Basic",
  status: "draft",
  module_count: 4,
  lessons_count: 8,
  hours: 12,
  modules: [],
  cover_image_url: "",
};

export const LEARNER_INITIAL = {
  full_name: "",
  email: "",
  enrollment_type: "manual",
  course_ids: [],
  note: "",
};

export const TASK_INITIAL = {
  title: "",
  description: "",
  assigned_to_user_id: "all",
  due_at: "",
  notes: "",
};

export function formatDuration(seconds) {
  const total = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export const tabs = [
  { id: "overview", label: "Overview" },
  { id: "courses", label: "Course management" },
  { id: "learners", label: "Learners" },
  { id: "enrollment", label: "Enrollment" },
  { id: "assignment_verification", label: "Assignment Verification" },
  { id: "quiz_attempts", label: "Quiz Attempts" },

  { id: "pal", label: "PAL tracker" },
  { id: "grading", label: "Grading Analytics" },
  { id: "tasks", label: "Tasks" },
  { id: "reports", label: "Reports" },
];

