const shortDateFormatter = new Intl.DateTimeFormat("en-IN", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const monthDateFormatter = new Intl.DateTimeFormat("en-IN", {
  month: "short",
  day: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatShortDate(value) {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : shortDateFormatter.format(parsed);
}

export function formatMonthDate(value) {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : monthDateFormatter.format(parsed);
}

export function formatDateTime(value) {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : dateTimeFormatter.format(parsed);
}

export function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "0%";
  }
  return `${Math.round(Number(value))}%`;
}

export function getScoreColor(score) {
  if (score >= 90) {
    return "#7C3AED";
  }
  if (score >= 75) {
    return "#2563EB";
  }
  if (score >= 60) {
    return "#059669";
  }
  if (score >= 45) {
    return "#D97706";
  }
  return "#DC2626";
}

export function getCompletionColor(score) {
  if (score >= 80) {
    return "#059669";
  }
  if (score >= 50) {
    return "#2563EB";
  }
  if (score >= 30) {
    return "#D97706";
  }
  return "#DC2626";
}

export function getStatusTone(value) {
  const normalized = String(value || "").toLowerCase();
  if (["active", "approved", "done", "completed", "success"].includes(normalized)) {
    return "success";
  }
  if (["pending", "in progress", "in_progress", "new", "draft", "manual", "overdue"].includes(normalized)) {
    return normalized === "manual" ? "brand" : "warn";
  }
  if (["rejected", "denied", "inactive", "failure", "archived"].includes(normalized)) {
    return "danger";
  }
  if (["self", "self-enrol", "self_enrol", "super admin", "super_admin"].includes(normalized)) {
    return "accent";
  }
  return "neutral";
}

export function getRoleLabel(user) {
  if (!user) {
    return "--";
  }
  if (user.role === "super_admin") {
    return "Super Admin";
  }
  if (user.role === "category_admin") {
    return user.category_scope ? titleize(user.category_scope) : "Category Admin";
  }
  if (user.role === "moodle_user") {
    return "Moodle User";
  }
  if (user.role && user.role !== "learner") {
    return titleize(user.role);
  }
  return "Learner";
}

export function titleize(value) {
  return String(value || "")
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function getInitials(value) {
  return String(value || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function getRankColor(rank) {
  if (rank === 1) {
    return "#D97706";
  }
  if (rank === 2) {
    return "#64748B";
  }
  if (rank === 3) {
    return "#92400E";
  }
  return "#94A3B8";
}
