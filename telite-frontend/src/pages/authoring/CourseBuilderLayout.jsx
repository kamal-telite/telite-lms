import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Button, IconButton, Badge, Modal, useToast } from "../../components/common/ui";
import { LessonBlockEditor } from "./LessonBlockEditor";
import { PublishToolbar } from "./PublishToolbar";
import { VersionHistoryPanel } from "./VersionHistoryPanel";
import { CoursePreviewModal } from "./CoursePreviewModal";
import { SyllabusTree } from "./SyllabusTree";
import { BuilderInspectorPanel } from "./BuilderInspectorPanel";
import { ProfileDropdown } from "../../layouts/DashboardLayout";
import { getInitials } from "../../utils/formatters";
import { api, getErrorMessage } from "../../services/client";
import { validateCourseForPublishing } from "../../services/publishValidation";
import { AuditLogViewer } from "./AuditLogViewer";
import { useCapability } from "../../hooks/useCapability";

export function CourseBuilderLayout({
  course,
  sections,
  setSections,
  onReloadStructure,
  lockExpiresAt,
  lockState,
  onBack,
  session,
  onLogout,
  initialModuleId,
  initialBlockId
}) {
  const { canEditStructure, canViewAudit } = useCapability();
  const { showToast } = useToast();
  const [activeModuleId, setActiveModuleId] = useState(initialModuleId || null);
  const [highlightBlockId, setHighlightBlockId] = useState(initialBlockId || null);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [courseStatus, setCourseStatus] = useState("draft");
  const [editorSaveState, setEditorSaveState] = useState({ state: "idle", lastSaved: null });
  const [showLockWarningModal, setShowLockWarningModal] = useState(false);
  const [showAuditLogModal, setShowAuditLogModal] = useState(false);
  const [sectionModalOpen, setSectionModalOpen] = useState(false);
  const [moduleModalSection, setModuleModalSection] = useState(null);
  const [sectionTitle, setSectionTitle] = useState("");
  const [moduleTitle, setModuleTitle] = useState("");
  const [moduleType, setModuleType] = useState("page");
  const [isCreatingStructure, setIsCreatingStructure] = useState(false);
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [activeBlock, setActiveBlock] = useState(null);
  const [blockSettingsUpdater, setBlockSettingsUpdater] = useState(null);

  const activeContext = useMemo(() => {
    for (const section of sections || []) {
      const module = (section.modules || []).find((item) => item.id === activeModuleId);
      if (module) {
        return { section, module };
      }
    }
    return { section: null, module: null };
  }, [sections, activeModuleId]);

  const handleFixValidation = useCallback((moduleId, blockId) => {
    setActiveModuleId(moduleId);
    if (blockId) {
      setHighlightBlockId(blockId);
    }
  }, []);

  useEffect(() => {
    if (initialModuleId && !activeModuleId) {
      setActiveModuleId(initialModuleId);
    }
    if (initialBlockId && !highlightBlockId) {
      setHighlightBlockId(initialBlockId);
    }
  }, [initialModuleId, initialBlockId]);

  useEffect(() => {
    if (course?.status) {
      setCourseStatus(course.status);
    }
  }, [course?.status]);

  useEffect(() => {
    if (!lockExpiresAt) return;
    
    const checkExpiry = () => {
      const expires = new Date(lockExpiresAt).getTime();
      const now = Date.now();
      const timeLeft = expires - now;
      
      // If less than 5 minutes (300,000 ms) and more than 0, show warning
      if (timeLeft > 0 && timeLeft <= 5 * 60 * 1000) {
        setShowLockWarningModal(true);
      } else {
        setShowLockWarningModal(false);
      }
    };
    
    const intervalId = setInterval(checkExpiry, 30000); // Check every 30 seconds
    checkExpiry();
    
    return () => clearInterval(intervalId);
  }, [lockExpiresAt]);

  const saveLabel = useMemo(() => {
    if (editorSaveState.state === "saving") return "Saving changes...";
    if (editorSaveState.state === "offline") return "Offline draft saved locally";
    if (editorSaveState.state === "conflict") return "Save conflict";
    if (editorSaveState.lastSaved) {
      return `Saved ${editorSaveState.lastSaved.toLocaleTimeString()}`;
    }
    return "No unsaved block changes";
  }, [editorSaveState]);

  const lockLabel = useMemo(() => {
    if (lockState === "lost") return "Lock connection lost";
    if (lockState === "blocked") return "Lock unavailable";
    if (lockState === "connecting") return "Lock connecting";
    if (!lockExpiresAt) return "Lock active";
    const expires = new Date(lockExpiresAt);
    if (Number.isNaN(expires.getTime())) return "Lock active";
    return `Lock until ${expires.toLocaleTimeString()}`;
  }, [lockExpiresAt, lockState]);

  const registerBlockSettingsUpdater = useCallback((updater) => {
    setBlockSettingsUpdater(() => updater);
  }, []);

  const handleActiveBlockChange = useCallback((block) => {
    setActiveBlock(block);
  }, []);

  const handleBlockSettingChange = useCallback((key, value) => {
    if (!activeBlock || !blockSettingsUpdater) return;

    blockSettingsUpdater(activeBlock.id || activeBlock._tempId, key, value);
    setActiveBlock((current) =>
      current
        ? { ...current, settings: { ...(current.settings || {}), [key]: value } }
        : current
    );
  }, [activeBlock, blockSettingsUpdater]);

  const openSectionModal = () => {
    if (!course?.id) return;
    setSectionTitle(`Section ${sections.length + 1}`);
    setSectionModalOpen(true);
  };

  const openModuleModal = (section) => {
    if (!course?.id || !section) return;
    setModuleModalSection(section);
    setModuleTitle("New module");
    setModuleType("page");
  };

  const handleCreateSection = async (event) => {
    event.preventDefault();
    if (!course?.id || !sectionTitle.trim()) return;

    setIsCreatingStructure(true);
    try {
      const { data } = await api.post(`/authoring/courses/${course.id}/sections`, {
        title: sectionTitle.trim(),
        sort_order: sections.length,
      });
      setSections([...(sections || []), { ...data, modules: [] }]);
      setSectionModalOpen(false);
      showToast("Section added.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to add section."), "error");
    } finally {
      setIsCreatingStructure(false);
    }
  };

  const handleCreateModule = async (event) => {
    event.preventDefault();
    if (!course?.id || !moduleModalSection || !moduleTitle.trim()) return;

    setIsCreatingStructure(true);
    try {
      const { data } = await api.post("/authoring/modules", {
        course_id: course.id,
        section: moduleModalSection.sort_order ?? 0,
        section_id: moduleModalSection.id || null,
        title: moduleTitle.trim(),
        module_type: moduleType,
      });
      const module = data.module;
      setSections((current) =>
        current.map((s) =>
          s.id === moduleModalSection.id
            ? { ...s, modules: [...(s.modules || []), module] }
            : s
        )
      );
      setActiveModuleId(module.id);
      setModuleModalSection(null);
      showToast("Module added.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to add module."), "error");
    } finally {
      setIsCreatingStructure(false);
    }
  };

  const openRenameSection = (section) => {
    if (section.id === 0) {
      showToast("The unassigned module group cannot be renamed.", "warning");
      return;
    }
    setRenameTarget({ type: "section", item: section });
    setRenameTitle(section.title || "");
  };

  const openRenameModule = (module) => {
    setRenameTarget({ type: "module", item: module });
    setRenameTitle(module.title || "");
  };

  const handleDuplicateSection = async (section) => {
    if (!course?.id || !section?.id || section.id === 0) {
      showToast("The unassigned module group cannot be duplicated.", "warning");
      return;
    }

    setIsCreatingStructure(true);
    try {
      const { data } = await api.post(`/authoring/courses/${course.id}/sections/${section.id}/duplicate`);
      const duplicatedSection = data.section;
      setSections((current) => [...(current || []), duplicatedSection]);
      const firstModule = duplicatedSection.modules?.[0];
      if (firstModule) {
        setActiveModuleId(firstModule.id);
      }
      showToast("Section duplicated.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Duplicate section failed."), "error");
    } finally {
      setIsCreatingStructure(false);
    }
  };

  const handleDuplicateModule = async (module) => {
    if (!module?.id) return;

    setIsCreatingStructure(true);
    try {
      const { data } = await api.post(`/authoring/modules/${module.id}/duplicate`);
      const duplicatedModule = data.module;
      setSections((current) =>
        current.map((section) =>
          section.id === duplicatedModule.section_id
            ? { ...section, modules: [...(section.modules || []), duplicatedModule] }
            : section
        )
      );
      setActiveModuleId(duplicatedModule.id);
      showToast("Module duplicated.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Duplicate module failed."), "error");
    } finally {
      setIsCreatingStructure(false);
    }
  };

  const handleRename = async (event) => {
    event.preventDefault();
    if (!renameTarget || !renameTitle.trim()) return;

    setIsCreatingStructure(true);
    try {
      if (renameTarget.type === "section") {
        const { data } = await api.patch(`/authoring/courses/${course.id}/sections/${renameTarget.item.id}`, {
          title: renameTitle.trim(),
        });
        setSections((current) =>
          current.map((section) => (section.id === data.id ? { ...section, title: data.title } : section))
        );
        showToast("Section renamed.", "success");
      } else {
        const { data } = await api.put(`/authoring/modules/${renameTarget.item.id}`, {
          title: renameTitle.trim(),
        });
        const updatedModule = data.module;
        setSections((current) =>
          current.map((section) => ({
            ...section,
            modules: (section.modules || []).map((module) =>
              module.id === updatedModule.id ? { ...module, title: updatedModule.title } : module
            ),
          }))
        );
        showToast("Module renamed.", "success");
      }
      setRenameTarget(null);
    } catch (err) {
      showToast(getErrorMessage(err, "Rename failed."), "error");
    } finally {
      setIsCreatingStructure(false);
    }
  };

  const openDeleteSection = (section) => {
    if (section.id === 0) {
      showToast("The unassigned module group cannot be deleted.", "warning");
      return;
    }
    setDeleteTarget({ type: "section", item: section });
  };

  const openDeleteModule = (module) => {
    setDeleteTarget({ type: "module", item: module });
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;

    setIsCreatingStructure(true);
    try {
      if (deleteTarget.type === "section") {
        await api.delete(`/authoring/courses/${course.id}/sections/${deleteTarget.item.id}`);
        setSections((current) => current.filter((section) => section.id !== deleteTarget.item.id));
        showToast("Section deleted.", "warning");
      } else {
        await api.delete(`/authoring/modules/${deleteTarget.item.id}`);
        setSections((current) =>
          current.map((section) => ({
            ...section,
            modules: (section.modules || []).filter((module) => module.id !== deleteTarget.item.id),
          }))
        );
        if (activeModuleId === deleteTarget.item.id) {
          setActiveModuleId(null);
          setActiveBlock(null);
        }
        showToast("Module deleted.", "warning");
      }
      setDeleteTarget(null);
    } catch (err) {
      showToast(getErrorMessage(err, "Delete failed."), "error");
    } finally {
      setIsCreatingStructure(false);
    }
  };
  
  const [validationStatus, setValidationStatus] = useState({ isValid: true, readinessScore: 100, errors: [], warnings: [] });

  useEffect(() => {
    let mounted = true;
    if (course?.id && editorSaveState.state === "idle") {
      validateCourseForPublishing(course.id).then((result) => {
        if (mounted) setValidationStatus(result);
      });
    }
    return () => { mounted = false; };
  }, [course?.id, sections, editorSaveState.state]);

  return (
    <div className="builder-layout" style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8fafc' }}>
      {/* Top Navbar */}
      <header style={{ 
        height: '60px', 
        borderBottom: '1px solid #e2e8f0', 
        display: 'flex', 
        alignItems: 'center', 
        padding: '0 20px', 
        background: '#fff',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <IconButton icon="arrow-left" label="Back to Admin" onClick={onBack} />
          <div>
            <div style={{ fontWeight: 600, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '12px' }}>
              {course?.name} 
              <Badge tone={courseStatus === "published" ? "success" : courseStatus === "review" ? "warning" : "accent"}>
                {courseStatus ? `${courseStatus.toUpperCase()} Mode` : "DRAFT Mode"}
              </Badge>
            </div>
            <div style={{ color: "#64748b", fontSize: "12px", marginTop: "2px" }}>
              {course?.id}
            </div>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {canViewAudit && (
            <Button tone="neutral" icon="list" onClick={() => setShowAuditLogModal(true)}>Audit Log</Button>
          )}
          <Button tone="neutral" icon="clock" onClick={() => setShowVersionHistory(!showVersionHistory)}>History</Button>
          <div style={{ fontSize: '12px', marginRight: '16px', textAlign: "right", lineHeight: 1.35, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "2px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: editorSaveState.state === "saving" ? "#d97706" : editorSaveState.state === "conflict" ? "#dc2626" : "#64748b" }}>
              {editorSaveState.state === "saving" && <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f59e0b", animation: "pulse 1.5s infinite" }} />}
              {saveLabel}
            </div>
            <div style={{ color: lockState === "lost" ? "#dc2626" : "#64748b" }}>{lockLabel}</div>
          </div>
          <Button tone="neutral" icon="eye" onClick={() => setShowPreviewModal(true)}>Preview</Button>
          <div style={{ width: '1px', height: '24px', background: '#e2e8f0', margin: '0 8px' }} />
          <ProfileDropdown 
            profile={{
              initials: getInitials(session?.user?.name || "Author"),
              gradient: ["#2563EB", "#059669"],
              name: session?.user?.name,
              roleLabel: "author",
            }} 
            onLogout={onLogout} 
          />
        </div>
      </header>
      
      <PublishToolbar 
        courseId={course?.id} 
        courseStatus={courseStatus} 
        onStatusChanged={setCourseStatus} 
        validationStatus={validationStatus} 
        onFixValidation={handleFixValidation}
      />
      
      {/* 3-Pane Body */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Left Pane: Syllabus */}
        <div style={{ 
          width: '320px', 
          borderRight: '1px solid #e2e8f0', 
          background: '#fff',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #e2e8f0', fontWeight: 600 }}>
            Syllabus
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
            <SyllabusTree 
              courseId={course?.id}
              sections={sections} 
              setSections={setSections} 
              activeModuleId={activeModuleId}
              onSelectModule={setActiveModuleId}
              onAddModule={openModuleModal}
              onRenameSection={openRenameSection}
              onDuplicateSection={handleDuplicateSection}
              onDeleteSection={openDeleteSection}
              onRenameModule={openRenameModule}
              onDuplicateModule={handleDuplicateModule}
              onDeleteModule={openDeleteModule}
              canEdit={canEditStructure}
            />
          </div>
          {canEditStructure && (
            <div style={{ padding: '16px', borderTop: '1px solid #e2e8f0' }}>
              <Button tone="neutral" style={{ width: '100%', justifyContent: 'center' }} icon="plus" onClick={openSectionModal}>
                Add Section
              </Button>
            </div>
          )}
        </div>
        
        {/* Center Pane: Editor (Stage 2) */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '40px', background: '#f8fafc' }}>
          {activeModuleId ? (
            <LessonBlockEditor
              courseId={course?.id}
              moduleId={activeModuleId}
              activeBlock={activeBlock}
              highlightBlockId={highlightBlockId}
              onHighlightClear={() => setHighlightBlockId(null)}
              onActiveBlockChange={handleActiveBlockChange}
              onRegisterBlockSettingsUpdater={registerBlockSettingsUpdater}
              onSaveStateChange={setEditorSaveState}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.2 }}>📄</div>
              <h3>Select a module to edit</h3>
              <p>Or add a new module to the syllabus on the left.</p>
            </div>
          )}
        </div>
        {/* Right Pane: Inspector / Version History */}
        {showVersionHistory ? (
          <div style={{ width: '320px', background: '#fff', borderLeft: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700, color: "#0f172a" }}>History</div>
              <Button tone="neutral" onClick={() => setShowVersionHistory(false)}>Inspector</Button>
            </div>
            <VersionHistoryPanel 
              courseId={course?.id} 
              currentVersion={{ id: 1, version_number: 1 }} // dummy 
              onVersionChanged={() => {
                setActiveModuleId(null);
                setActiveBlock(null);
                onReloadStructure?.();
              }}
            />
          </div>
        ) : (
          <BuilderInspectorPanel
            course={course}
            activeSection={activeContext.section}
            activeModule={activeContext.module}
            activeBlock={activeBlock}
            onBlockSettingChange={handleBlockSettingChange}
            validationStatus={validationStatus}
            lockState={lockLabel}
            onOpenHistory={() => setShowVersionHistory(true)}
          />
        )}
        
      </div>

      <CoursePreviewModal 
        open={showPreviewModal} 
        onClose={() => setShowPreviewModal(false)} 
        courseId={course?.id} 
        courseName={course?.name} 
      />

      <Modal
        open={showAuditLogModal}
        onClose={() => setShowAuditLogModal(false)}
        title={`Audit Trail: ${course?.name}`}
        width={1000}
        footer={<Button tone="neutral" onClick={() => setShowAuditLogModal(false)}>Close</Button>}
      >
        <div style={{ height: "70vh" }}>
          <AuditLogViewer courseId={course?.id} />
        </div>
      </Modal>

      <Modal
        open={showLockWarningModal}
        onClose={() => setShowLockWarningModal(false)}
        title="Lock Expiring Soon"
        width={400}
        footer={<Button tone="primary" onClick={() => setShowLockWarningModal(false)}>Understood</Button>}
      >
        <p style={{ margin: 0, color: "#991b1b", lineHeight: 1.5 }}>
          <strong>Warning:</strong> Your editing lock for this course will expire in less than 5 minutes. 
          Please save your work or refresh your session to renew the lock.
        </p>
      </Modal>

      <Modal
        open={sectionModalOpen}
        onClose={() => setSectionModalOpen(false)}
        title="Create Section"
        width={440}
        footer={
          <>
            <Button tone="neutral" onClick={() => setSectionModalOpen(false)}>Cancel</Button>
            <Button tone="primary" type="submit" form="create-section-form" disabled={!sectionTitle.trim() || isCreatingStructure}>
              {isCreatingStructure ? "Creating..." : "Create Section"}
            </Button>
          </>
        }
      >
        <form id="create-section-form" onSubmit={handleCreateSection}>
          <label className="field">
            <span className="field__label">Section Name *</span>
            <input
              className="field__input"
              value={sectionTitle}
              onChange={(event) => setSectionTitle(event.target.value)}
              autoFocus
            />
          </label>
        </form>
      </Modal>

      <Modal
        open={Boolean(moduleModalSection)}
        onClose={() => setModuleModalSection(null)}
        title="Create Module"
        width={440}
        footer={
          <>
            <Button tone="neutral" onClick={() => setModuleModalSection(null)}>Cancel</Button>
            <Button tone="primary" type="submit" form="create-module-form" disabled={!moduleTitle.trim() || isCreatingStructure}>
              {isCreatingStructure ? "Creating..." : "Create Module"}
            </Button>
          </>
        }
      >
        <form id="create-module-form" onSubmit={handleCreateModule}>
          <label className="field">
            <span className="field__label">Module Name *</span>
            <input
              className="field__input"
              value={moduleTitle}
              onChange={(event) => setModuleTitle(event.target.value)}
              autoFocus
            />
          </label>
          <label className="field" style={{ marginTop: "16px" }}>
            <span className="field__label">Module Type</span>
            <select
              className="field__input"
              value={moduleType}
              onChange={(event) => setModuleType(event.target.value)}
            >
              <option value="page">Lesson page</option>
              <option value="quiz">Quiz</option>
              <option value="resource">Resource</option>
              <option value="assignment">Assignment shell</option>
            </select>
          </label>
        </form>
      </Modal>

      <Modal
        open={Boolean(renameTarget)}
        onClose={() => setRenameTarget(null)}
        title={renameTarget?.type === "section" ? "Rename Section" : "Rename Module"}
        width={440}
        footer={
          <>
            <Button tone="neutral" onClick={() => setRenameTarget(null)}>Cancel</Button>
            <Button tone="primary" type="submit" form="rename-structure-form" disabled={!renameTitle.trim() || isCreatingStructure}>
              {isCreatingStructure ? "Saving..." : "Save Name"}
            </Button>
          </>
        }
      >
        <form id="rename-structure-form" onSubmit={handleRename}>
          <label className="field">
            <span className="field__label">Name *</span>
            <input
              className="field__input"
              value={renameTitle}
              onChange={(event) => setRenameTitle(event.target.value)}
              autoFocus
            />
          </label>
        </form>
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title={deleteTarget?.type === "section" ? "Delete Section" : "Delete Module"}
        width={440}
        footer={
          <>
            <Button tone="neutral" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button tone="danger" onClick={handleDelete} disabled={isCreatingStructure}>
              {isCreatingStructure ? "Deleting..." : "Delete"}
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, color: "#475569", lineHeight: 1.5 }}>
          {deleteTarget?.type === "section"
            ? "Delete this section only if it has no modules. Move or delete its modules first."
            : "Delete this module from the builder. Its lesson blocks will no longer appear in the syllabus."}
        </p>
      </Modal>
    </div>
  );
}
