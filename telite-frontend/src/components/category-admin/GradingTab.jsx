import { StatCard, Panel, LoadingState, EmptyState } from "../../components/common/ui";
import { ChartCanvas } from "../../components/common/charts";
import { formatShortDate, titleize } from "../../utils/formatters";

export default function GradingTab({ 
  gradingAnalytics, 
  gradingLoading, 
  gradingFilters, 
  setGradingFilters, 
  filteredGradingLearners, 
  filteredAssessmentDetails 
}) {
  return (
    <>
      {gradingLoading ? (
        <LoadingState title="Loading grading analytics..." body="Fetching grade data for your category." />
      ) : gradingAnalytics ? (
        <>
          <div className="grid-4">
            <StatCard accent="#2563EB" label="Total Learners" value={gradingAnalytics.total_learners} meta="In this category" />
            <StatCard accent="#7C3AED" label="Total Assessments" value={gradingAnalytics.total_assessments} meta="Quiz and assignment rows" />
            <StatCard accent="#F59E0B" label="Pending Evaluations" value={gradingAnalytics.pending_evaluations} meta="Awaiting review or grading" />
            <StatCard accent="#059669" label="Evaluated Assessments" value={gradingAnalytics.evaluated_assessments} meta="Gradebook results" />
          </div>
          <div className="grid-4" style={{ marginTop: 18 }}>
            <StatCard accent="#7C3AED" label="Average Quiz Score" value={`${gradingAnalytics.quiz_average}%`} meta="Auto-graded quiz results" />
            <StatCard accent="#059669" label="Average Assignment Score" value={`${gradingAnalytics.assignment_average}%`} meta="Graded assignments" />
            <StatCard accent="#2563EB" label="Overall Course Average" value={`${gradingAnalytics.overall_course_average}%`} meta="All evaluated assessments" />
            <StatCard accent="#DC2626" label="Pass / Fail Rate" value={`${gradingAnalytics.pass_rate}% / ${gradingAnalytics.fail_rate}%`} meta="Pass threshold 60%" />
          </div>

          <Panel title="Filters" subtitle="Refine learner grades and assessment details" style={{ marginTop: 18 }}>
            <div className="grid-4">
              <label className="field"><span>Course</span><select value={gradingFilters.course} onChange={(e) => setGradingFilters((v) => ({ ...v, course: e.target.value }))}><option value="">All courses</option>{(gradingAnalytics.filters?.courses || []).map((course) => <option key={course.id} value={course.id}>{course.name}</option>)}</select></label>
              <label className="field"><span>Learner</span><select value={gradingFilters.learner} onChange={(e) => setGradingFilters((v) => ({ ...v, learner: e.target.value }))}><option value="">All learners</option>{(gradingAnalytics.filters?.learners || []).map((learner) => <option key={learner.id} value={learner.id}>{learner.name}</option>)}</select></label>
              <label className="field"><span>Assessment Type</span><select value={gradingFilters.type} onChange={(e) => setGradingFilters((v) => ({ ...v, type: e.target.value }))}><option value="">All types</option><option value="quiz">Quiz</option><option value="assignment">Assignment</option></select></label>
              <label className="field"><span>Status</span><select value={gradingFilters.status} onChange={(e) => setGradingFilters((v) => ({ ...v, status: e.target.value }))}><option value="">All statuses</option>{(gradingAnalytics.filters?.statuses || []).map((status) => <option key={status} value={status}>{titleize(status)}</option>)}</select></label>
              <label className="field"><span>Grade</span><select value={gradingFilters.grade} onChange={(e) => setGradingFilters((v) => ({ ...v, grade: e.target.value }))}><option value="">All grades</option>{(gradingAnalytics.filters?.grades || []).map((grade) => <option key={grade} value={grade}>{grade}</option>)}</select></label>
              <label className="field"><span>From</span><input type="date" value={gradingFilters.from} onChange={(e) => setGradingFilters((v) => ({ ...v, from: e.target.value }))} /></label>
              <label className="field"><span>To</span><input type="date" value={gradingFilters.to} onChange={(e) => setGradingFilters((v) => ({ ...v, to: e.target.value }))} /></label>
              <label className="field"><span>Search</span><input value={gradingFilters.search} onChange={(e) => setGradingFilters((v) => ({ ...v, search: e.target.value }))} placeholder="Learner or course" /></label>
            </div>
          </Panel>

          <div className="grid-2-wide" style={{ marginTop: 18 }}>
            <Panel title="Grade Distribution" subtitle="Evaluated assessment grades"><ChartCanvas type="bar" height={220} labels={(gradingAnalytics.grade_distribution || []).map((g) => g.grade)} datasets={[{ label: "Learners", data: (gradingAnalytics.grade_distribution || []).map((g) => g.count), backgroundColor: "#2563EB", borderRadius: 8 }]} options={{ plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }} /></Panel>
            <Panel title="Pass vs Fail" subtitle="Learner course outcomes"><ChartCanvas type="doughnut" height={220} labels={(gradingAnalytics.pass_fail || []).map((p) => p.label)} datasets={[{ data: (gradingAnalytics.pass_fail || []).map((p) => p.value), backgroundColor: ["#059669", "#DC2626"] }]} options={{ plugins: { legend: { position: "bottom" } } }} /></Panel>
          </div>
          <div className="grid-2-wide" style={{ marginTop: 18 }}>
            <Panel title="Quiz Average" subtitle="Current quiz gradebook results"><ChartCanvas type="bar" height={200} labels={["Quiz"]} datasets={[{ label: "Average", data: [gradingAnalytics.quiz_average], backgroundColor: "#7C3AED", borderRadius: 8 }]} options={{ plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }} /></Panel>
            <Panel title="Assignment Average" subtitle="Current assignment gradebook results"><ChartCanvas type="bar" height={200} labels={["Assignment"]} datasets={[{ label: "Average", data: [gradingAnalytics.assignment_average], backgroundColor: "#059669", borderRadius: 8 }]} options={{ plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }} /></Panel>
          </div>
          <Panel title="Course Performance" subtitle="Average grades by course" style={{ marginTop: 18 }}><ChartCanvas type="bar" height={220} labels={(gradingAnalytics.course_performance || []).map((c) => c.course_name)} datasets={[{ label: "Average Grade", data: (gradingAnalytics.course_performance || []).map((c) => c.average), backgroundColor: "#2563EB", borderRadius: 8 }]} options={{ plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }} /></Panel>

          <div className="grid-2-wide" style={{ marginTop: 18 }}>
            <Panel title="Top Performers" subtitle="Highest overall grades"><div className="table-wrap"><table><thead><tr><th>Learner</th><th style={{ textAlign: "right" }}>Grade</th></tr></thead><tbody>{(gradingAnalytics.top_performers || []).length ? gradingAnalytics.top_performers.map((learner, idx) => <tr key={idx}><td>{learner.full_name}</td><td className="mono" style={{ textAlign: "right", color: "#059669", fontWeight: 700 }}>{learner.grade}%</td></tr>) : <tr><td colSpan="2"><EmptyState title="No top performers yet" body="Learners with evaluated grades will appear here." /></td></tr>}</tbody></table></div></Panel>
            <Panel title="Lowest Performers" subtitle="Lowest overall grades"><div className="table-wrap"><table><thead><tr><th>Learner</th><th style={{ textAlign: "right" }}>Grade</th></tr></thead><tbody>{(gradingAnalytics.lowest_performers || []).length ? gradingAnalytics.lowest_performers.map((learner, idx) => <tr key={idx}><td>{learner.full_name}</td><td className="mono" style={{ textAlign: "right", color: learner.grade < 60 ? "#DC2626" : "#2563EB", fontWeight: 700 }}>{learner.grade}%</td></tr>) : <tr><td colSpan="2"><EmptyState title="No graded learners yet" body="Learner grades will appear after evaluation." /></td></tr>}</tbody></table></div></Panel>
          </div>

          <Panel title="Learner Grade Table" subtitle="Per-learner course grading analytics" style={{ marginTop: 18 }}>
            <div className="table-wrap"><table><thead><tr><th>Learner Name</th><th>Email</th><th>Course</th><th>Quiz Avg</th><th>Assignment Avg</th><th>Grade</th><th>Overall %</th><th>Completed</th><th>Pending</th><th>PAL Score</th><th>Certificate Eligible</th></tr></thead><tbody>{filteredGradingLearners.length ? filteredGradingLearners.map((row) => <tr key={`${row.learner_id}-${row.course_id}`}><td>{row.learner_name}</td><td>{row.email}</td><td>{row.course}</td><td className="mono">{row.quiz_average}%</td><td className="mono">{row.assignment_average}%</td><td>{row.overall_grade}</td><td className="mono">{row.overall_percentage}%</td><td>{row.completed_assessments}</td><td>{row.pending_assessments}</td><td className="mono">{row.pal_score}%</td><td>{row.certificate_eligible}</td></tr>) : <tr><td colSpan="11"><EmptyState title="No learner grades match the filters" body="Adjust filters or wait for grading activity." /></td></tr>}</tbody></table></div>
          </Panel>

          <Panel title="Assessment Details" subtitle="Quiz and assignment grading records" style={{ marginTop: 18 }}>
            <div className="table-wrap"><table><thead><tr><th>Assessment</th><th>Type</th><th>Learner</th><th>Course</th><th>Marks</th><th>Max</th><th>%</th><th>Grade</th><th>Status</th><th>Submission Date</th><th>Evaluation Date</th><th>Evaluator</th></tr></thead><tbody>{filteredAssessmentDetails.length ? filteredAssessmentDetails.map((row, idx) => <tr key={`${row.assessment_type}-${row.learner_name}-${idx}`}><td>{row.assessment_name || row.quiz_name || row.assignment_name}</td><td>{titleize(row.assessment_type)}</td><td>{row.learner_name}</td><td>{row.course}</td><td className="mono">{row.marks_obtained ?? "-"}</td><td className="mono">{row.maximum_marks ?? "-"}</td><td className="mono">{row.percentage == null ? "-" : `${row.percentage}%`}</td><td>{row.grade}</td><td>{titleize(row.status)}</td><td>{formatShortDate(row.submission_date)}</td><td>{formatShortDate(row.evaluation_date)}</td><td>{row.evaluator}</td></tr>) : <tr><td colSpan="12"><EmptyState title="No assessment details match the filters" body="Quiz and assignment grading records will appear here." /></td></tr>}</tbody></table></div>
          </Panel>
        </>
      ) : (
        <EmptyState title="No grading data available" body="Grading analytics will appear once courses have been graded." />
      )}
    </>
  );
}
