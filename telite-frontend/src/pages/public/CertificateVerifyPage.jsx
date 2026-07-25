import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LoadingState, ErrorState, EmptyState } from "../../components/common/ui";
import { api } from "../../services/client";
import "../../styles/components/certificate-verify.css";

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
    <div className="cert-verify-page">
      <div className="cert-verify-card">
        <div className="cert-verify-card__border" aria-hidden="true" />
        <div className="cert-verify-card__corner cert-verify-card__corner--tl" aria-hidden="true" />
        <div className="cert-verify-card__corner cert-verify-card__corner--tr" aria-hidden="true" />
        <div className="cert-verify-card__corner cert-verify-card__corner--bl" aria-hidden="true" />
        <div className="cert-verify-card__corner cert-verify-card__corner--br" aria-hidden="true" />
        <div className="cert-verify-card__watermark" aria-hidden="true">Verified</div>

        <div className="cert-verify-content">
          <div className="cert-verify-badge">✓ Verified Certificate</div>

          <h1 className="cert-verify-title">Certificate of Completion</h1>

          <p className="cert-verify-lead">This certificate is proudly presented to</p>

          <h2 className="cert-verify-recipient">{certificate.issued_to}</h2>

          <p className="cert-verify-body">has successfully completed the course</p>

          <h3 className="cert-verify-course">{certificate.course_name}</h3>

          <div className="cert-verify-meta">
            <div className="cert-verify-meta__item">
              <div className="cert-verify-meta__label">Date Issued</div>
              <div className="cert-verify-meta__value">
                {new Date(certificate.issued_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </div>
            </div>

            <div className="cert-verify-meta__item">
              <div className="cert-verify-meta__label">Certificate ID</div>
              <div className="cert-verify-meta__value">
                {certificate.hash?.substring(0, 8).toUpperCase()}
              </div>
            </div>

            <div className="cert-verify-meta__item">
              <div className="cert-verify-meta__label">Status</div>
              <div className="cert-verify-meta__value cert-verify-meta__value--valid">✓ Valid</div>
            </div>
          </div>

          <div className="cert-verify-hash">
            <div className="cert-verify-hash__label">Verification Hash</div>
            <div className="cert-verify-hash__value">{certificate.hash}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
