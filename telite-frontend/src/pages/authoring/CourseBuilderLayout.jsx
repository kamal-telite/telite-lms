import React, { useMemo, useState } from "react";
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

export function CourseBuilderLayout({
  course,
  sections,
  setSections,
  onBack,
  session,
  onLogout
}) {
  const { showToast } = useToast();
  const [activeModuleId, setActiveModuleId] = useState(null);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [courseStatus, setCourseStatus] = useState("draft");
  const [sectionModalOpen, setSectionModalOpen] = useState(false);
  const [moduleModalSection, setModuleModalSection] = useState(null);
  const [sectionTitle, setSectionTitle] = useState("");
  const [moduleTitle, setModuleTitle] = useState("");
  const [moduleDuration, setModuleDuration] = useState("30 mins");
  const [isCreatingStructure, setIsCreatingStructure] = useState(false);
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);

  const activeContext = useMemo(() => {
    for (const section of sections || []) {
      const module = (section.modules || []).find((item) => item.id === activeModuleId);
      if (module) {
        return { section, module };
      }
    }
    return { section: null, module: null };
  }, [sections, activeModuleId]);

  const openSectionModal = () => {
    if (!course?.id) return;
    setSectionTitle(`Section ${sections.length + 1}`);
    setSectionModalOpen(true);
  };

  const openModuleModal = (section) => {
    if (!course?.id || !section) return;
    setModuleModalSection(section);
    setModuleTitle("New module");
    setModuleDuration("30 mins");
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
        module_type: "page",
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
  
  // Derive real validation from the syllabus tree:
  // valid if course has a name, at least one section, and every section has at least one module
  const validationStatus = {
    isValid: (
      Boolean(course?.name) &&
      Array.isArray(sections) &&
      sections.length > 0 &&
      sections.every(s => Array.isArray(s.modules) && s.modules.length > 0)
    ),
    errors: (() => {
      const errs = [];
      if (!course?.name) errs.push("Course has no title.");
      if (!sections || sections.length === 0) errs.push("Add at least one section.");
      else {
        sections.forEach((s, i) => {
          if (!s.modules || s.modules.length === 0)
            errs.push(`Section ${i + 1} ("${s.title || "Untitled"}") has no modules.`);
        });
      }
      return errs;
    })(),
  };

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
              <Badge tone="accent">Draft Mode</Badge>
            </div>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Button tone="neutral" icon="clock" onClick={() => setShowVersionHistory(!showVersionHistory)}>History</Button>
          <div style={{ fontSize: '13px', color: '#64748b', marginRight: '16px' }}>
            Autosaved just now
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
        onSelectModule={setActiveModuleId}
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
              onDeleteSection={openDeleteSection}
              onRenameModule={openRenameModule}
              onDeleteModule={openDeleteModule}
            />
          </div>
          <div style={{ padding: '16px', borderTop: '1px solid #e2e8f0' }}>
            <Button tone="neutral" style={{ width: '100%', justifyContent: 'center' }} icon="plus" onClick={openSectionModal}>
              Add Section
            </Button>
          </div>
        </div>
        
        {/* Center Pane: Editor (Stage 2) */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '40px', background: '#f8fafc' }}>
          {activeModuleId ? (
            <LessonBlockEditor courseId={course?.id} moduleId={activeModuleId} />
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
            />
          </div>
        ) : (
          <BuilderInspectorPanel
            course={course}
            activeSection={activeContext.section}
            activeModule={activeContext.module}
            validationStatus={validationStatus}
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
            <span className="field__label">Duration</span>
            <input
              className="field__input"
              value={moduleDuration}
              onChange={(event) => setModuleDuration(event.target.value)}
            />
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
