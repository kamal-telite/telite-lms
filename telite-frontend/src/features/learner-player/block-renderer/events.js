import { api } from "../../../services/client";

export function postLearnerEvents(events) {
  return api.post("/api/v1/learner/events", { events }).catch(() => {});
}
