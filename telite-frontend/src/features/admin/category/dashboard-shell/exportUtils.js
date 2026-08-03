import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { titleize } from "../../../../utils/formatters";

export function exportCategoryCsv({ activeTab, dashboard, learners, palCards }) {
  let csvContent = "";
  if (activeTab === "overview" || activeTab === "courses") {
    csvContent = "Course,Tier,Enrolled,Completion,Status\n" +
      (dashboard?.courses || []).map(c => `"${c.name}",${c.tier},${c.enrolled_count},${c.completion_pct}%,${c.status}`).join("\n");
  } else if (activeTab === "learners") {
    csvContent = "Name,Email,Courses,PAL Score,Enrollment Type\n" +
      (learners || []).map(l => `"${l.full_name}","${l.email}",${l.courses_completed}/${l.total_courses},${l.pal_score}%,${l.enrollment_type}`).join("\n");
  } else if (activeTab === "enrollment") {
    csvContent = "Name,Email,Request Type,Requested At,Domain Verified\n" +
      (dashboard?.enrollment_requests || []).map(r => `"${r.full_name}","${r.email || ""}",${r.request_type},${r.requested_at},${r.domain_verified}`).join("\n");
  } else if (activeTab === "pal") {
    csvContent = "Name,Completion %,Quiz Avg,Time (h),PAL Score\n" +
      (palCards || []).map(l => `"${l.full_name}",${l.pal_completion_pct},${Math.round(l.pal_quiz_avg)},${Math.round(l.pal_time_spent_hours)},${l.pal_score}`).join("\n");
  } else {
    csvContent = "Category Summary Export\nTab," + activeTab + "\nExported," + new Date().toISOString();
  }
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `telite_${activeTab}_export_${new Date().toISOString().slice(0,10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export function exportCategoryPdf({ activeTab, dashboard, learners, palCards }) {
  const doc = new jsPDF();
  doc.text(`Telite LMS Export - ${titleize(activeTab)}`, 14, 15);
  doc.setFontSize(10);
  doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, 22);

  let head = [];
  let body = [];
  if (activeTab === "overview" || activeTab === "courses") {
    head = [["Course", "Tier", "Enrolled", "Completion", "Status"]];
    body = (dashboard?.courses || []).map(c => [c.name, c.tier, c.enrolled_count, `${c.completion_pct}%`, c.status]);
  } else if (activeTab === "learners") {
    head = [["Name", "Email", "Courses", "PAL Score", "Enrollment Type"]];
    body = (learners || []).map(l => [l.full_name, l.email, `${l.courses_completed}/${l.total_courses}`, `${l.pal_score}%`, l.enrollment_type]);
  } else if (activeTab === "enrollment") {
    head = [["Name", "Email", "Type", "Requested", "Domain Verified"]];
    body = (dashboard?.enrollment_requests || []).map(r => [r.full_name, r.email || "", r.request_type, r.requested_at, r.domain_verified ? "Yes" : "No"]);
  } else if (activeTab === "pal") {
    head = [["Name", "Completion %", "Quiz Avg", "Time (h)", "PAL Score"]];
    body = (palCards || []).map(l => [l.full_name, `${l.pal_completion_pct}%`, `${Math.round(l.pal_quiz_avg)}%`, `${Math.round(l.pal_time_spent_hours)}h`, l.pal_score]);
  } else {
    head = [["Tab", "Exported At"]];
    body = [[activeTab, new Date().toISOString()]];
  }

  autoTable(doc, { startY: 28, head, body, theme: "striped", headStyles: { fillColor: [37, 99, 235] } });
  doc.save(`telite_${activeTab}_export_${new Date().toISOString().slice(0,10)}.pdf`);
}
