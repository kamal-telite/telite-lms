import React, { useMemo, useState } from "react";
import { Badge, Button, Modal } from "../common/ui";
import { createQuestionImportJob } from "../../api/questionBank";
import { buildQuestionImportPayload, getImportStatusTone } from "../../utils/questionImportJob";

export default function QuestionImportWizard({
  open,
  onClose,
  categories = [],
  tags = [],
  loadingTaxonomy = false,
}) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileKey, setFileKey] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [selectedTags, setSelectedTags] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");

  const selectedTagNames = useMemo(
    () => tags.filter((tag) => selectedTags.includes(Number(tag.id))).map((tag) => tag.name),
    [tags, selectedTags]
  );

  const payload = useMemo(
    () => buildQuestionImportPayload({
      fileName: selectedFile?.name,
      fileKey,
      categoryId,
      tagIds: selectedTags,
    }),
    [selectedFile, fileKey, categoryId, selectedTags]
  );

  const canSubmit = Boolean(payload.file_key) && !submitting;

  const resetAndClose = () => {
    setSelectedFile(null);
    setFileKey("");
    setCategoryId("");
    setSelectedTags([]);
    setSubmitting(false);
    setJob(null);
    setError("");
    onClose();
  };

  const toggleTag = (tagId) => {
    const numericId = Number(tagId);
    setSelectedTags((current) =>
      current.includes(numericId)
        ? current.filter((item) => item !== numericId)
        : [...current, numericId]
    );
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError("");
    try {
      const result = await createQuestionImportJob(payload);
      setJob(result);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || "Failed to create import job");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={resetAndClose}
      title="Import Questions"
      description="Create an import job and apply taxonomy to every imported question."
      width={720}
    >
      <div className="question-import-wizard">
        <div className="question-import-steps" aria-label="Import workflow">
          <span className="question-import-step is-active">Upload</span>
          <span className="question-import-step">Taxonomy</span>
          <span className="question-import-step">Job Status</span>
        </div>

        <div className="question-import-grid">
          <div className="question-import-main">
            <div className="field">
              <label className="field__label" htmlFor="question-import-file">Question file</label>
              <input
                id="question-import-file"
                className="field__input"
                type="file"
                accept=".csv,.txt,.aiken"
                onChange={(event) => {
                  const file = event.target.files?.[0] || null;
                  setSelectedFile(file);
                  if (file && !fileKey.trim()) {
                    setFileKey(`imports/${file.name}`);
                  }
                }}
              />
              <div className="field__help">CSV, TXT, or Aiken files are accepted by the import pipeline.</div>
            </div>

            <div className="field">
              <label className="field__label" htmlFor="question-import-file-key">File key</label>
              <input
                id="question-import-file-key"
                className="field__input"
                value={fileKey}
                onChange={(event) => setFileKey(event.target.value)}
                placeholder="imports/questions.csv"
              />
            </div>

            <div className="field">
              <label className="field__label" htmlFor="question-import-category">Category</label>
              <select
                id="question-import-category"
                className="field__input"
                value={categoryId}
                onChange={(event) => setCategoryId(event.target.value)}
                disabled={loadingTaxonomy}
              >
                <option value="">No category</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>{category.label || category.name}</option>
                ))}
              </select>
            </div>

            <div className="field">
              <label className="field__label">Tags</label>
              <div className="question-editor-tag-select">
                {tags.length === 0 ? (
                  <span className="row-subtitle">No tags available</span>
                ) : tags.map((tag) => (
                  <button
                    key={tag.id}
                    type="button"
                    className="question-editor-tag"
                    onClick={() => toggleTag(tag.id)}
                  >
                    <Badge tone={selectedTags.includes(Number(tag.id)) ? "brand" : "neutral"}>{tag.name}</Badge>
                  </button>
                ))}
              </div>
            </div>

            {error ? <div className="question-import-error">{error}</div> : null}
          </div>

          <aside className="question-import-summary" aria-label="Import summary">
            <h4>Submission</h4>
            <dl>
              <div>
                <dt>File key</dt>
                <dd>{payload.file_key || "--"}</dd>
              </div>
              <div>
                <dt>Category ID</dt>
                <dd>{payload.category_id || "--"}</dd>
              </div>
              <div>
                <dt>Tags</dt>
                <dd>{selectedTagNames.length ? selectedTagNames.join(", ") : "--"}</dd>
              </div>
            </dl>
            {job ? (
              <div className="question-import-job">
                <span className="row-subtitle">Import job</span>
                <strong>{job.id}</strong>
                <Badge tone={getImportStatusTone(job.status)}>{job.status}</Badge>
              </div>
            ) : null}
          </aside>
        </div>

        <div className="split-actions question-import-actions">
          <Button tone="ghost" onClick={resetAndClose}>Close</Button>
          <Button tone="primary" icon="upload" onClick={handleSubmit} disabled={!canSubmit}>
            {submitting ? "Creating..." : "Create Import Job"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
