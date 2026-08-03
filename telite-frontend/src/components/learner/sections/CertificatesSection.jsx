import { Button, Panel, EmptyState, LoadingState } from "../../common/ui";
import { buildCertificateDownloadUrl } from "../../../utils/certificateUrls";

/**
 * CertificatesSection - View and download earned certificates
 */
export function CertificatesSection({
  certificates,
  certificatesLoading,
  learnerName,
  courses = [],
}) {
  return (
    <section id="section-certificates">
      <Panel title="Certificates" subtitle="Earned credentials">
        {certificatesLoading ? (
          <LoadingState
            title="Loading certificates..."
            body="Fetching your earned certificates."
          />
        ) : certificates.length > 0 ? (
          <div className="grid-3">
            {certificates.map((cert) => {
              const courseId = String(cert.course_id);
              
              // Find matching course to get thumbnail
              const matchedCourse = courses.find(
                (c) => String(c.id || c.course_id) === courseId
              );
              const courseImageUrl = matchedCourse?.cover_image_url;

              const certNumber = cert.certificate_hash
                ? cert.certificate_hash.substring(0, 8).toUpperCase()
                : "N/A";
              const issueDate = cert.issued_at
                ? new Date(cert.issued_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })
                : "N/A";

              return (
                <div
                  className="soft-card"
                  key={cert.id}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 16,
                    padding: "20px",
                    borderRadius: "16px",
                    border: "1px solid var(--border-subtle, rgba(255,255,255,0.08))",
                    background: "var(--surface-raised, rgba(255,255,255,0.02))",
                    boxShadow: "var(--shadow-card, 0 4px 20px rgba(0,0,0,0.05))"
                  }}
                >
                  {courseImageUrl ? (
                    <div
                      style={{
                        position: "relative",
                        width: "100%",
                        aspectRatio: "16 / 9",
                        borderRadius: "10px",
                        overflow: "hidden",
                        background: "var(--surface-3, #f1f5f9)"
                      }}
                    >
                      <img
                        src={courseImageUrl}
                        loading="lazy"
                        alt={cert.course_name}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover"
                        }}
                      />
                      <div
                        style={{
                          position: "absolute",
                          inset: 0,
                          background: "linear-gradient(to bottom, rgba(0,0,0,0.1) 60%, rgba(0,0,0,0.3) 100%)",
                          pointerEvents: "none"
                        }}
                      />
                    </div>
                  ) : (
                    <div
                      style={{
                        background:
                          "var(--brand-gradient, linear-gradient(135deg, #0ea5e9, #6366f1))",
                        width: "100%",
                        aspectRatio: "16 / 9",
                        borderRadius: "10px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                        fontWeight: "bold",
                        fontSize: "32px",
                      }}
                    >
                      🎓
                    </div>
                  )}
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div className="row-title" style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>
                      {cert.course_name || "Course"}
                    </div>
                    <div className="row-subtitle" style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      {learnerName}
                    </div>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "12px",
                      color: "var(--text-muted)",
                    }}
                  >
                    <span>ID: {certNumber}</span>
                    <span>{issueDate}</span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 8,
                      marginTop: "auto",
                    }}
                  >
                    <Button
                      tone="primary"
                      size="sm"
                      onClick={() => {
                        const url = buildCertificateDownloadUrl(courseId, {
                          inline: true,
                          baseUrl: import.meta.env?.VITE_API_BASE_URL || "",
                        });
                        window.open(url, "_blank", "noopener,noreferrer");
                      }}
                      style={{ flex: 1 }}
                    >
                      View
                    </Button>
                    <Button
                      tone="ghost"
                      size="sm"
                      onClick={() => {
                        const url = buildCertificateDownloadUrl(courseId, {
                          inline: false,
                          baseUrl: import.meta.env?.VITE_API_BASE_URL || "",
                        });
                        window.open(url, "_blank", "noopener,noreferrer");
                      }}
                      style={{ flex: 1 }}
                    >
                      Download
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="No certificates yet"
            body="Complete your first course to earn a certificate."
          />
        )}
      </Panel>
    </section>
  );
}
