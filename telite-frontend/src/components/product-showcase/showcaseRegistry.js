import AnalyticsShowcase from "./AnalyticsShowcase";
import DashboardPreview from "./DashboardPreview";
import IntegrationPreview from "./IntegrationPreview";
import LearnerExperience from "./LearnerExperience";

export const showcaseRegistry = [
  {
    id: "analytics",
    title: "Operational Intelligence",
    description: "Predictive learner health, live risk signals, and intervention guidance.",
    glow: "var(--showcase-glow-analytics)",
    Component: AnalyticsShowcase,
  },
  {
    id: "admin",
    title: "Admin Control Center",
    description: "Multi-tenant oversight with uptime, onboarding, and sync discipline.",
    glow: "var(--showcase-glow-admin)",
    Component: DashboardPreview,
  },
  {
    id: "integrations",
    title: "Ecosystem Mesh",
    description: "Live Moodle-centered orchestration across APIs, webhooks, and comms.",
    glow: "var(--showcase-glow-integrations)",
    Component: IntegrationPreview,
  },
  {
    id: "learner",
    title: "Learner Workspace",
    description: "Progress momentum, coaching prompts, and achievement states in one flow.",
    glow: "var(--showcase-glow-learner)",
    Component: LearnerExperience,
  },
];
