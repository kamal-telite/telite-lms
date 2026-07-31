import { StatCard, Panel, Button, LoadingState, EmptyState, Badge } from "../../components/common/ui";
import { titleize } from "../../utils/formatters";

export default function QuizAttemptsTab({ 
  quizStatistics, 
  quizStatsLoading, 
  loadQuizStatistics 
}) {
  return (
    <div className="dashboard-stack">
      <div className="grid-4">
        <StatCard accent="#2563EB" label="Learners" value={(quizStatistics.rows || []).length} meta="With quiz visibility" />
        <StatCard accent="#7C3AED" label="Attempts Used" value={(quizStatistics.rows || []).reduce((sum, row) => sum + Number(row.attempts_used || 0), 0)} meta="Across all quizzes" />
        <StatCard accent="#059669" label="Highest Score" value={`${Math.round(Math.max(0, ...(quizStatistics.rows || []).map((row) => Number(row.highest_score || 0))))}%`} meta="Best learner score" />
        <StatCard accent="#D97706" label="Avg Score" value={`${Math.round((quizStatistics.rows || []).reduce((sum, row) => sum + Number(row.average_score || 0), 0) / Math.max(1, (quizStatistics.rows || []).filter((row) => Number(row.attempts_used || 0) > 0).length))}%`} meta="Attempted learners" />
      </div>
      <Panel 
        title="Quiz Attempts" 
        subtitle="Attempts used, remaining, best score, and status for every learner"
        action={<Button tone="ghost" onClick={loadQuizStatistics} disabled={quizStatsLoading}>{quizStatsLoading ? "Loading..." : "Refresh"}</Button>}
      >
        {quizStatsLoading ? (
          <LoadingState title="Loading quiz attempts..." body="Fetching learner attempt history." />
        ) : (quizStatistics.rows || []).length === 0 ? (
          <EmptyState title="No quiz data found" body="Learner quiz attempts will appear here once quizzes are submitted." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Learner</th>
                  <th style={{ textAlign: "right" }}>Used</th>
                  <th style={{ textAlign: "right" }}>Remaining</th>
                  <th style={{ textAlign: "right" }}>Highest</th>
                  <th style={{ textAlign: "right" }}>Latest</th>
                  <th style={{ textAlign: "right" }}>Average</th>
                  <th>Status</th>
                  <th>Quiz Details</th>
                </tr>
              </thead>
              <tbody>
                {(quizStatistics.rows || []).map((row) => (
                  <tr key={row.learner?.id}>
                    <td>
                      <div className="row-title">{row.learner?.full_name}</div>
                      <div className="row-subtitle">{row.learner?.email}</div>
                    </td>
                    <td className="mono" style={{ textAlign: "right" }}>{row.attempts_used}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{row.attempts_remaining === null ? "Unlimited" : row.attempts_remaining}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{Math.round(row.highest_score || 0)}%</td>
                    <td className="mono" style={{ textAlign: "right" }}>{row.latest_score === null || row.latest_score === undefined ? "-" : `${Math.round(row.latest_score)}%`}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{Math.round(row.average_score || 0)}%</td>
                    <td><Badge tone={row.completion_status === "completed" ? "success" : row.completion_status === "attempted" ? "warn" : "neutral"}>{titleize(String(row.completion_status || "not_started").replace("_", " "))}</Badge></td>
                    <td style={{ minWidth: 260 }}>
                      {(row.quizzes || []).length ? (
                        <div style={{ display: "grid", gap: 6 }}>
                          {(row.quizzes || []).map((quiz) => (
                            <div key={quiz.block_id} className="row-subtitle">
                              <strong>{quiz.quiz_title}</strong>: {quiz.attempts_used} used, {quiz.attempts_remaining === null ? "Unlimited" : `${quiz.attempts_remaining} left`}, best {Math.round(quiz.highest_score || 0)}%
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="muted">No quizzes assigned</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
