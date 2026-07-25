import { Panel, StatCard, EmptyState, LoadingState, Badge } from "../../common/ui";
import { ChartCanvas } from "../../common/charts";
import {
  formatPercent,
  getScoreColor,
  titleize,
  formatDateTime,
} from "../../../utils/formatters";

/**
 * GradingSection - Learner grades and assessment results
 */
export function GradingSection({ gradingAnalytics, gradingLoading }) {
  if (gradingLoading) {
    return (
      <section id="section-grading">
        <LoadingState
          title="Loading your grades..."
          body="Fetching your grade data from the system."
        />
      </section>
    );
  }

  if (!gradingAnalytics) {
    return (
      <section id="section-grading">
        <EmptyState
          title="No grading data available"
          body="Grading analytics will appear once courses have been graded."
        />
      </section>
    );
  }

  if (!gradingAnalytics.has_grades) {
    return (
      <section id="section-grading">
        <EmptyState
          title={gradingAnalytics.message || "No grades available"}
          body="Your grades will appear here once your assessments have been evaluated."
        />
      </section>
    );
  }

  return (
    <section id="section-grading">
      <div className="grid-4">
        <StatCard
          accent="#7C3AED"
          label="Overall Grade"
          value={
            gradingAnalytics.overall_grade ||
            `${gradingAnalytics.final_grade}%`
          }
          meta={`${gradingAnalytics.final_grade}% overall`}
        />
        <StatCard
          accent="#2563EB"
          label="Completed Assessments"
          value={gradingAnalytics.completed_assessments || 0}
          meta={`${gradingAnalytics.pending_evaluations || 0} pending`}
        />
        <StatCard
          accent="#059669"
          label="Quiz Average"
          value={`${gradingAnalytics.quiz_average}%`}
          meta="Assessment performance"
        />
        <StatCard
          accent="#F59E0B"
          label="Assignment Average"
          value={`${gradingAnalytics.assignment_average}%`}
          meta="Task performance"
        />
      </div>

      <div className="grid-4" style={{ marginTop: 18 }}>
        <StatCard
          accent="#2563EB"
          label="Overall Percentage"
          value={`${gradingAnalytics.current_percentage}%`}
          meta="Live gradebook average"
        />
        <StatCard
          accent="#059669"
          label="Highest Score"
          value={`${gradingAnalytics.highest_score || 0}%`}
          meta="Best assessment"
        />
        <StatCard
          accent="#DC2626"
          label="Lowest Score"
          value={`${gradingAnalytics.lowest_score || 0}%`}
          meta="Lowest graded item"
        />
        <StatCard
          accent="#7C3AED"
          label="Status"
          value={gradingAnalytics.pass_fail_status}
          meta="Current standing"
        />
      </div>

      <Panel
        title="Assessment Grades"
        subtitle="Quizzes, assignments, feedback, and evaluation status"
        style={{ marginTop: 18 }}
      >
        {(gradingAnalytics.assessments || []).length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Course</th>
                  <th>Assessment</th>
                  <th>Type</th>
                  <th style={{ textAlign: "right" }}>Marks</th>
                  <th style={{ textAlign: "right" }}>Percentage</th>
                  <th>Grade</th>
                  <th>Status</th>
                  <th>Submitted</th>
                  <th>Evaluated</th>
                  <th>Evaluator</th>
                  <th>Feedback</th>
                </tr>
              </thead>
              <tbody>
                {(gradingAnalytics.assessments || []).map((item) => (
                  <tr key={item.id}>
                    <td>{item.course_name}</td>
                    <td>
                      <div className="row-title">
                        {item.assessment_name || item.quiz_name || item.assignment_name}
                      </div>
                      {item.attempt_number ? (
                        <div className="row-subtitle">
                          Attempt {item.attempt_number}
                          {item.attempts_remaining !== null &&
                          item.attempts_remaining !== undefined
                            ? ` · ${item.attempts_remaining} left`
                            : ""}
                        </div>
                      ) : null}
                    </td>
                    <td>{item.assessment_type}</td>
                    <td className="mono" style={{ textAlign: "right" }}>
                      {item.marks_obtained ?? "-"} / {item.maximum_marks ?? "-"}
                    </td>
                    <td
                      className="mono"
                      style={{
                        textAlign: "right",
                        color:
                          item.percentage !== null &&
                          item.percentage !== undefined
                            ? getScoreColor(item.percentage)
                            : undefined,
                        fontWeight: 700,
                      }}
                    >
                      {item.percentage !== null &&
                      item.percentage !== undefined
                        ? `${item.percentage}%`
                        : "-"}
                    </td>
                    <td>{item.grade || "-"}</td>
                    <td>
                      <Badge
                        tone={
                          item.status === "graded" || item.status === "approved"
                            ? "success"
                            : item.status === "rejected"
                            ? "danger"
                            : "warn"
                        }
                      >
                        {titleize(
                          String(item.status || "pending").replace("_", " ")
                        )}
                      </Badge>
                    </td>
                    <td className="mono">
                      {item.submission_date
                        ? formatDateTime(item.submission_date)
                        : "-"}
                    </td>
                    <td className="mono">
                      {item.evaluation_date
                        ? formatDateTime(item.evaluation_date)
                        : "-"}
                    </td>
                    <td>{item.evaluator_name || "-"}</td>
                    <td>{item.feedback || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No assessment grades yet"
            body="Quiz and assignment grades will appear here after evaluation."
          />
        )}
      </Panel>

      <Panel
        title="Course Grades"
        subtitle="Course completion and assessment averages"
        style={{ marginTop: 18 }}
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th style={{ textAlign: "right" }}>Completion</th>
                <th style={{ textAlign: "right" }}>Quiz Avg</th>
                <th style={{ textAlign: "right" }}>Assignment Avg</th>
                <th style={{ textAlign: "right" }}>Course Grade</th>
                <th>Certificate</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {gradingAnalytics.grade_summary.map((grade, idx) => (
                <tr key={idx}>
                  <td>{grade.course_name}</td>
                  <td className="mono" style={{ textAlign: "right" }}>
                    {formatPercent(grade.completion_percentage || 0)}
                  </td>
                  <td className="mono" style={{ textAlign: "right" }}>
                    {formatPercent(grade.average_quiz_score || 0)}
                  </td>
                  <td className="mono" style={{ textAlign: "right" }}>
                    {formatPercent(grade.average_assignment_score || 0)}
                  </td>
                  <td
                    className="mono"
                    style={{
                      textAlign: "right",
                      color: getScoreColor(grade.percentage),
                      fontWeight: 700,
                    }}
                  >
                    {grade.percentage}%{" "}
                    {grade.display_grade ? `(${grade.display_grade})` : ""}
                  </td>
                  <td>
                    <Badge
                      tone={
                        grade.certificate_eligibility ? "success" : "neutral"
                      }
                    >
                      {grade.certificate_eligibility ? "Eligible" : "Not yet"}
                    </Badge>
                  </td>
                  <td>
                    <Badge tone={grade.passed ? "success" : "danger"}>
                      {grade.passed ? "Pass" : "Fail"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel
        title="Grade Progress"
        subtitle="Your performance across courses"
        style={{ marginTop: 18 }}
      >
        <ChartCanvas
          type="bar"
          height={200}
          labels={gradingAnalytics.grade_progress.map((g) => g.course_name)}
          datasets={[
            {
              label: "Grade",
              data: gradingAnalytics.grade_progress.map((g) => g.percentage),
              backgroundColor: gradingAnalytics.grade_progress.map((g) =>
                getScoreColor(g.percentage)
              ),
              borderRadius: 8,
            },
          ]}
          options={{
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, max: 100 } },
          }}
        />
      </Panel>
    </section>
  );
}
