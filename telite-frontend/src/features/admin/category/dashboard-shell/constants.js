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

export function buildCategoryAdminNavGroups({ kpis = {}, tasks = [], assignmentQueueStats = {} } = {}) {
  const taskCount = Array.isArray(tasks) ? tasks.length : 0;
  const pendingAssignments = Number(assignmentQueueStats?.pending || 0);

  return [
    {
      label: "Overview",
      items: [
        { id: "dashboard", label: "Dashboard", icon: "dashboard" },
        { id: "activity", label: "Activity feed", icon: "reports" },
      ],
    },
    {
      label: "Management",
      items: [
        { id: "courses", label: "Courses", icon: "course", badge: String(kpis.total_courses || 0), badgeTone: "brand" },
        { id: "question_banks", label: "Question banks", icon: "database" },
        { id: "announcements", label: "Announcements", icon: "bell" },
        { id: "learners", label: "Learners", icon: "users", badge: String(kpis.active_learners || 0), badgeTone: "brand" },
        { id: "enrollment", label: "Enrollment", icon: "enrollments", badge: String(kpis.pending_enrollment || 0), badgeTone: "warn" },
        { id: "assignment_verification", label: "Assignment verification", icon: "task", badge: String(pendingAssignments), badgeTone: "warn" },
        { id: "tasks", label: "Tasks", icon: "task", badge: String(taskCount), badgeTone: "neutral" },
      ],
    },
    {
      label: "Analytics",
      items: [
        { id: "pal", label: "PAL tracking", icon: "leaderboard" },
        { id: "reports", label: "Reports", icon: "analytics" },
      ],
    },
    {
      label: "Settings",
      items: [{ id: "settings", label: "Settings", icon: "settings" }],
    },
  ];
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

