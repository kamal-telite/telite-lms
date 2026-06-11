import { api } from "./client";

export async function validateCourseForPublishing(courseId) {
  try {
    const { data } = await api.get(`/authoring/courses/${courseId}/validate`);
    // data is already { summary: ValidationSummary, results: ValidationResultItem[] }
    return data;
  } catch (err) {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail;
    const message = detail ? `Failed to validate course (${status}: ${detail})` : "Failed to validate course.";
    return {
      summary: { errors: 1, warnings: 0, infos: 0, score: 0 },
      results: [
        { type: "system", severity: "error", message }
      ]
    };
  }
}
