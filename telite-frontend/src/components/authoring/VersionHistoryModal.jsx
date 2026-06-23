import React, { useEffect, useMemo, useState } from "react";
import { Modal, Badge, EmptyState } from "../common/ui";
import { getQuestionVersions } from "../../services/client";

export default function VersionHistoryModal({ open, onClose, bankId, questionId, categories = [], tags = [] }) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);

  const categoryById = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories]
  );
  const tagById = useMemo(
    () => new Map(tags.map((tag) => [tag.id, tag])),
    [tags]
  );

  useEffect(() => {
    if (!open || !questionId) {
      return;
    }

    async function loadVersions() {
      setLoading(true);
      try {
        const data = await getQuestionVersions(bankId, questionId);
        setVersions(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    loadVersions();
  }, [open, bankId, questionId]);

  return (
    <Modal open={open} onClose={onClose} title="Version History" size="medium">
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {loading ? (
          <div style={{ padding: 20, textAlign: "center" }}>Loading history...</div>
        ) : versions.length === 0 ? (
          <EmptyState title="No versions found" />
        ) : (
          <div className="activity-list">
            {versions.map((version) => (
              <div
                key={version.id}
                className="activity-item"
                style={{ opacity: version.status === "ARCHIVED" ? 0.6 : 1 }}
              >
                <div style={{ flex: 1 }}>
                  <div className="row-title">{version.question_text}</div>
                  <div className="row-subtitle">
                    ID: {version.id} | Created {new Date(version.created_at).toLocaleString()}
                  </div>
                  <div className="version-history-taxonomy">
                    <Badge tone="neutral">
                      {version.category_id
                        ? categoryById.get(version.category_id)?.label || `Category #${version.category_id}`
                        : "No category"}
                    </Badge>
                    {(version.tag_ids || []).length === 0 ? (
                      <Badge tone="neutral">No tags</Badge>
                    ) : (
                      version.tag_ids.map((tagId) => (
                        <Badge key={tagId} tone="neutral">
                          {tagById.get(tagId)?.name || `Tag #${tagId}`}
                        </Badge>
                      ))
                    )}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <Badge tone={version.status === "PUBLISHED" ? "success" : version.status === "DRAFT" ? "neutral" : "warn"}>
                    {version.status}
                  </Badge>
                  {version.is_current_published && <Badge tone="brand">Current Published</Badge>}
                  {version.is_current_draft && <Badge tone="accent">Current Draft</Badge>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
