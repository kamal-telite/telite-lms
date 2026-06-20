import React, { useEffect, useMemo, useState } from "react";
import { Badge, Button } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";

const STATUS_TONES = {
  draft: "neutral",
  submitted: "info",
  resubmitted: "warning",
  graded: "success",
  returned: "danger",
};

function formatDate(value) {
  if (!value) return "Not submitted";
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function getFiles(submission) {
  if (Array.isArray(submission?.files)) return submission.files;
  if (Array.isArray(submission?.submission_files_json)) return submission.submission_files_json;
  return [];
}

export function AssignmentSubmissionsPanel({ blockId }) {
  const [submissions, setSubmissions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [grade, setGrade] = useState("");
  const [feedback, setFeedback] = useState("");
  const [returned, setReturned] = useState(false);

  const selectedSubmission = useMemo(
    () => submissions.find((submission) => submission.id === selectedId) || submissions[0] || null,
    [submissions, selectedId]
  );

  useEffect(() => {
    let isMounted = true;
    if (!blockId) return undefined;
    setLoading(true);
    setError("");
    api.get(`/api/v1/admin/assignments/${blockId}/submissions`)
      .then(({ data }) => {
        if (!isMounted) return;
        const nextSubmissions = Array.isArray(data.submissions) ? data.submissions : [];
        setSubmissions(nextSubmissions);
        setSelectedId(nextSubmissions[0]?.id || null);
      })
      .catch((requestError) => {
        if (!isMounted) return;
        setError(getErrorMessage(requestError, "Unable to load assignment submissions."));
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [blockId]);

  useEffect(() => {
    if (!selectedSubmission) {
      setGrade("");
      setFeedback("");
      setReturned(false);
      return;
    }
    setGrade(selectedSubmission.grade ?? "");
    setFeedback(selectedSubmission.feedback || "");
    setReturned(selectedSubmission.status === "returned");
  }, [selectedSubmission]);

  const handleGrade = async () => {
    if (!selectedSubmission) return;
    setSaving(true);
    setError("");
    try {
      const { data } = await api.post(`/api/v1/admin/submissions/${selectedSubmission.id}/grade`, {
        grade: grade === "" ? null : Number(grade),
        feedback,
        returned,
      });
      const updated = data.submission;
      setSubmissions((current) =>
        current.map((submission) => (submission.id === updated.id ? updated : submission))
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Unable to grade assignment submission."));
    } finally {
      setSaving(false);
    }
  };

  if (!blockId) {
    return (
      <section className="inspector-section">
        <div className="inspector-section__title">Assignment Submissions</div>
        <div className="inspector-section__body">
          <p className="assignment-admin-panel__empty">Save this block before reviewing submissions.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="inspector-section assignment-admin-panel">
      <div className="inspector-section__title">Assignment Submissions</div>
      <div className="inspector-section__body">
        {loading ? <p className="assignment-admin-panel__empty">Loading submissions...</p> : null}
        {error ? <div className="assignment-admin-panel__error">{error}</div> : null}

        {!loading && submissions.length === 0 ? (
          <p className="assignment-admin-panel__empty">No learner submissions yet.</p>
        ) : null}

        {submissions.length > 0 ? (
          <div className="assignment-admin-panel__list">
            {submissions.map((submission) => (
              <button
                key={submission.id}
                type="button"
                className={`assignment-admin-panel__item ${
                  selectedSubmission?.id === submission.id ? "assignment-admin-panel__item--active" : ""
                }`}
                onClick={() => setSelectedId(submission.id)}
              >
                <span>
                  Learner #{submission.learner_id || submission.user_id}
                  <small>{formatDate(submission.submitted_at)}</small>
                </span>
                <Badge tone={STATUS_TONES[submission.status] || "neutral"}>
                  {submission.status}
                </Badge>
              </button>
            ))}
          </div>
        ) : null}

        {selectedSubmission ? (
          <div className="assignment-admin-panel__detail">
            <div className="assignment-admin-panel__meta">
              <span>Attempt {selectedSubmission.attempt_number || 1}</span>
              <span>{formatDate(selectedSubmission.submitted_at)}</span>
            </div>

            <div>
              <label className="assignment-admin-panel__label">Submission text</label>
              <div className="assignment-admin-panel__response">
                {selectedSubmission.submission_text || "No written response."}
              </div>
            </div>

            {getFiles(selectedSubmission).length > 0 ? (
              <div>
                <label className="assignment-admin-panel__label">Attachments</label>
                <div className="assignment-admin-panel__files">
                  {getFiles(selectedSubmission).map((file, index) => {
                    const assetId = file.asset_id || file.id || index;
                    const label = file.original_filename || file.filename || `Attachment ${index + 1}`;
                    return (
                      <a
                        key={assetId}
                        href={`/api/v1/submissions/${selectedSubmission.id}/download?asset_id=${encodeURIComponent(assetId)}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {label}
                      </a>
                    );
                  })}
                </div>
              </div>
            ) : null}

            <label className="assignment-admin-panel__label">
              Grade
              <input
                className="field__input"
                type="number"
                min="0"
                step="0.01"
                value={grade}
                onChange={(event) => setGrade(event.target.value)}
                placeholder="Optional score"
              />
            </label>

            <label className="assignment-admin-panel__label">
              Feedback
              <textarea
                className="field__input"
                value={feedback}
                onChange={(event) => setFeedback(event.target.value)}
                placeholder="Feedback for the learner"
                rows={4}
              />
            </label>

            <label className="assignment-admin-panel__check">
              <input
                type="checkbox"
                checked={returned}
                onChange={(event) => setReturned(event.target.checked)}
              />
              Return for revision
            </label>

            <Button tone="primary" onClick={handleGrade} disabled={saving}>
              {saving ? "Saving..." : "Save Grade"}
            </Button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
