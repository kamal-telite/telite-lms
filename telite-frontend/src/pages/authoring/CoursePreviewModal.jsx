import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Modal, Button, Badge, LoadingState, ErrorState } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";
import { BlockRenderer } from "../../components/player/BlockRenderer";

function flattenModules(sections = []) {
  return sections.flatMap((section) =>
    (section.modules || []).map((module) => ({
      ...module,
      section_id: section.id,
      section_title: section.title,
    }))
  );
}

export function CoursePreviewModal({ open, onClose, courseId, courseName }) {
  const [role, setRole] = useState("learner");
  const [courseData, setCourseData] = useState(null);
  const [activeModuleId, setActiveModuleId] = useState(null);
  const [blocks, setBlocks] = useState([]);
  const [loadingStructure, setLoadingStructure] = useState(false);
  const [loadingBlocks, setLoadingBlocks] = useState(false);
  const [error, setError] = useState(null);

  const modules = useMemo(() => flattenModules(courseData?.sections || []), [courseData]);
  const activeModule = useMemo(
    () => modules.find((module) => module.id === activeModuleId) || null,
    [modules, activeModuleId]
  );

  const loadStructure = useCallback(async () => {
    if (!courseId) return;

    setLoadingStructure(true);
    setError(null);
    try {
      const { data } = await api.get(`/authoring/courses/${courseId}/builder`);
      setCourseData(data);
      const firstModule = flattenModules(data.sections || [])[0];
      setActiveModuleId((current) => current || firstModule?.id || null);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load course preview."));
    } finally {
      setLoadingStructure(false);
    }
  }, [courseId]);

  const loadBlocks = useCallback(async () => {
    if (!courseId || !activeModuleId) {
      setBlocks([]);
      return;
    }

    setLoadingBlocks(true);
    try {
      const { data } = await api.get(`/authoring/courses/${courseId}/modules/${activeModuleId}/blocks`);
      setBlocks(data.blocks || []);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load module preview."));
    } finally {
      setLoadingBlocks(false);
    }
  }, [courseId, activeModuleId]);

  useEffect(() => {
    if (open) {
      loadStructure();
    }
  }, [open, loadStructure]);

  useEffect(() => {
    if (open) {
      loadBlocks();
    }
  }, [open, loadBlocks]);

  const roleLabel = {
    learner: "Learner Preview",
    cat_admin: "Category Admin Preview",
    super_admin: "Super Admin Preview",
  }[role];

  return (
    <Modal open={open} onClose={onClose} title={`Preview: ${courseName || "Course"}`} width="1100px">
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px", padding: "12px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
        <div style={{ fontWeight: 600, color: "#475569", display: "flex", alignItems: "center", marginRight: "16px" }}>Preview As:</div>
        <Button tone={role === "learner" ? "primary" : "neutral"} onClick={() => setRole("learner")}>Learner</Button>
        <Button tone={role === "cat_admin" ? "primary" : "neutral"} onClick={() => setRole("cat_admin")}>Category Admin</Button>
        <Button tone={role === "super_admin" ? "primary" : "neutral"} onClick={() => setRole("super_admin")}>Super Admin</Button>
      </div>

      <div style={{
        border: "1px solid #dbe3ef",
        borderRadius: "12px",
        height: "620px",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        background: "#fff",
      }}>
        <div style={{ background: "#f8fafc", padding: "12px 18px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0" }}>
          <div>
            <div style={{ color: "#0f172a", fontWeight: 700 }}>{roleLabel}</div>
            <div style={{ color: "#64748b", fontSize: "12px", marginTop: "2px" }}>
              Rendering current builder structure without learner progress tracking.
            </div>
          </div>
          <Badge tone="neutral">{courseData?.course?.status || "draft"}</Badge>
        </div>

        {loadingStructure ? (
          <LoadingState title="Loading course preview..." />
        ) : error ? (
          <ErrorState body={error} action={<Button tone="primary" onClick={loadStructure}>Retry</Button>} />
        ) : (
          <div style={{ display: "flex", minHeight: 0, flex: 1 }}>
            <aside style={{ width: "280px", borderRight: "1px solid #e2e8f0", background: "#f8fafc", display: "flex", flexDirection: "column" }}>
              <div style={{ padding: "16px", borderBottom: "1px solid #e2e8f0" }}>
                <div style={{ fontWeight: 700, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {courseData?.course?.name || courseName}
                </div>
                <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                  {modules.length} module(s)
                </div>
              </div>
              <div style={{ overflowY: "auto", padding: "10px" }}>
                {modules.map((module, index) => {
                  const isActive = module.id === activeModuleId;
                  return (
                    <button
                      key={module.id}
                      type="button"
                      onClick={() => setActiveModuleId(module.id)}
                      style={{
                        width: "100%",
                        display: "flex",
                        gap: "10px",
                        alignItems: "flex-start",
                        textAlign: "left",
                        padding: "10px",
                        border: `1px solid ${isActive ? "#bfdbfe" : "transparent"}`,
                        borderRadius: "8px",
                        background: isActive ? "#eff6ff" : "transparent",
                        color: "#0f172a",
                        cursor: "pointer",
                      }}
                    >
                      <span style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "999px",
                        background: isActive ? "#2563eb" : "#e2e8f0",
                        color: isActive ? "#fff" : "#475569",
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "12px",
                        flexShrink: 0,
                      }}>
                        {index + 1}
                      </span>
                      <span style={{ minWidth: 0 }}>
                        <span style={{ display: "block", fontWeight: 700, fontSize: "13px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {module.title}
                        </span>
                        <span style={{ display: "block", color: "#64748b", fontSize: "12px", marginTop: "2px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {module.section_title || "Course modules"}
                        </span>
                      </span>
                    </button>
                  );
                })}
                {modules.length === 0 ? (
                  <div style={{ padding: "16px", color: "#64748b", fontSize: "13px", textAlign: "center" }}>
                    No modules available to preview.
                  </div>
                ) : null}
              </div>
            </aside>

            <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
              <header style={{ padding: "16px 22px", borderBottom: "1px solid #e2e8f0", background: "#fff" }}>
                <div style={{ color: "#64748b", fontSize: "12px", fontWeight: 700, textTransform: "uppercase" }}>
                  {activeModule?.section_title || "Course modules"}
                </div>
                <h3 style={{ margin: "4px 0 0", color: "#0f172a" }}>{activeModule?.title || "Select a module"}</h3>
              </header>

              <div style={{ flex: 1, overflowY: "auto", padding: "28px", background: "#fff" }}>
                <div style={{ maxWidth: "820px", margin: "0 auto" }}>
                  {loadingBlocks ? (
                    <LoadingState title="Loading module blocks..." />
                  ) : activeModule ? (
                    blocks.length > 0 ? (
                      <BlockRenderer content={blocks} />
                    ) : (
                      <div style={{ border: "1px dashed #cbd5e1", borderRadius: "8px", padding: "40px", textAlign: "center", color: "#64748b", background: "#f8fafc" }}>
                        This module has no visible blocks yet.
                      </div>
                    )
                  ) : (
                    <div style={{ border: "1px dashed #cbd5e1", borderRadius: "8px", padding: "40px", textAlign: "center", color: "#64748b", background: "#f8fafc" }}>
                      Select a module from the preview sidebar.
                    </div>
                  )}
                </div>
              </div>
            </main>
          </div>
        )}
      </div>
    </Modal>
  );
}
