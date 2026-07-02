import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LoadingState, ErrorState, EmptyState } from "../../components/common/ui";
import { api } from "../../services/client";

export default function CertificateVerifyPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [certificate, setCertificate] = useState(null);

  useEffect(() => {
    async function verifyCertificate() {
      try {
        const { data } = await api.get(`/public/verify/${token}`);
        setCertificate(data);
      } catch (err) {
        setError(err?.response?.data?.detail || "Invalid or expired certificate");
      } finally {
        setLoading(false);
      }
    }
    if (token) {
      verifyCertificate();
    }
  }, [token]);

  if (loading) return <LoadingState title="Verifying certificate..." />;
  if (error) return <ErrorState body={error} />;
  if (!certificate) return <EmptyState title="Certificate not found" />;

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px"
    }}>
      <div style={{
        background: "white",
        borderRadius: "20px",
        boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
        maxWidth: "1000px",
        width: "100%",
        padding: "60px",
        position: "relative",
        overflow: "hidden"
      }}>
        {/* Decorative border */}
        <div style={{
          position: "absolute",
          top: "20px",
          left: "20px",
          right: "20px",
          bottom: "20px",
          border: "3px solid #667eea",
          borderRadius: "15px",
          pointerEvents: "none"
        }} />

        {/* Corner decorations */}
        <div style={{
          position: "absolute",
          top: "30px",
          left: "30px",
          width: "80px",
          height: "80px",
          borderTop: "5px solid #764ba2",
          borderLeft: "5px solid #764ba2",
          pointerEvents: "none"
        }} />
        <div style={{
          position: "absolute",
          top: "30px",
          right: "30px",
          width: "80px",
          height: "80px",
          borderTop: "5px solid #764ba2",
          borderRight: "5px solid #764ba2",
          pointerEvents: "none"
        }} />
        <div style={{
          position: "absolute",
          bottom: "30px",
          left: "30px",
          width: "80px",
          height: "80px",
          borderBottom: "5px solid #764ba2",
          borderLeft: "5px solid #764ba2",
          pointerEvents: "none"
        }} />
        <div style={{
          position: "absolute",
          bottom: "30px",
          right: "30px",
          width: "80px",
          height: "80px",
          borderBottom: "5px solid #764ba2",
          borderRight: "5px solid #764ba2",
          pointerEvents: "none"
        }} />

        {/* Watermark */}
        <div style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%) rotate(-30deg)",
          fontSize: "120px",
          fontWeight: "bold",
          color: "rgba(102, 126, 234, 0.05)",
          textTransform: "uppercase",
          pointerEvents: "none",
          whiteSpace: "nowrap"
        }}>
          Verified
        </div>

        {/* Content */}
        <div style={{ position: "relative", zIndex: 1, textAlign: "center" }}>
          <div style={{
            display: "inline-block",
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            color: "white",
            padding: "8px 24px",
            borderRadius: "20px",
            fontSize: "14px",
            fontWeight: "600",
            textTransform: "uppercase",
            letterSpacing: "2px",
            marginBottom: "30px"
          }}>
            ✓ Verified Certificate
          </div>

          <h1 style={{
            fontSize: "48px",
            fontWeight: "bold",
            color: "#1e293b",
            margin: "0 0 10px 0",
            textTransform: "uppercase",
            letterSpacing: "3px"
          }}>
            Certificate of Completion
          </h1>

          <p style={{
            fontSize: "18px",
            color: "#64748b",
            margin: "0 0 40px 0",
            fontStyle: "italic"
          }}>
            This certificate is proudly presented to
          </p>

          <h2 style={{
            fontSize: "42px",
            fontWeight: "bold",
            color: "#667eea",
            margin: "30px 0",
            textDecoration: "underline",
            textDecorationColor: "#764ba2",
            textDecorationThickness: "3px"
          }}>
            {certificate.issued_to}
          </h2>

          <p style={{
            fontSize: "20px",
            color: "#475569",
            margin: "20px 0"
          }}>
            has successfully completed the course
          </p>

          <h3 style={{
            fontSize: "36px",
            fontWeight: "bold",
            color: "#1e293b",
            margin: "20px 0"
          }}>
            {certificate.course_name}
          </h3>

          <div style={{
            display: "flex",
            justifyContent: "space-around",
            marginTop: "60px",
            borderTop: "2px solid #e2e8f0",
            paddingTop: "30px"
          }}>
            <div>
              <div style={{
                fontSize: "12px",
                color: "#64748b",
                textTransform: "uppercase",
                letterSpacing: "2px",
                marginBottom: "8px"
              }}>
                Date Issued
              </div>
              <div style={{
                fontSize: "18px",
                fontWeight: "bold",
                color: "#1e293b"
              }}>
                {new Date(certificate.issued_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric"
                })}
              </div>
            </div>

            <div>
              <div style={{
                fontSize: "12px",
                color: "#64748b",
                textTransform: "uppercase",
                letterSpacing: "2px",
                marginBottom: "8px"
              }}>
                Certificate ID
              </div>
              <div style={{
                fontSize: "18px",
                fontWeight: "bold",
                color: "#1e293b"
              }}>
                {certificate.hash?.substring(0, 8).toUpperCase()}
              </div>
            </div>

            <div>
              <div style={{
                fontSize: "12px",
                color: "#64748b",
                textTransform: "uppercase",
                letterSpacing: "2px",
                marginBottom: "8px"
              }}>
                Status
              </div>
              <div style={{
                fontSize: "18px",
                fontWeight: "bold",
                color: "#10b981"
              }}>
                ✓ Valid
              </div>
            </div>
          </div>

          <div style={{
            marginTop: "40px",
            padding: "20px",
            background: "#f8fafc",
            borderRadius: "10px",
            border: "1px solid #e2e8f0"
          }}>
            <div style={{
              fontSize: "12px",
              color: "#64748b",
              marginBottom: "5px"
            }}>
              Verification Hash
            </div>
            <div style={{
              fontSize: "11px",
              color: "#94a3b8",
              fontFamily: "monospace",
              wordBreak: "break-all"
            }}>
              {certificate.hash}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
