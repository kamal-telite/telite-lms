import React, { useEffect, useState, useMemo, useRef } from "react";
import { api } from "../../services/client";
import { useCountdownTimer } from "../../hooks/useCountdownTimer";

function formatTime(seconds) {
  if (!seconds || seconds === 0) return null;
  const total = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${total}s`;
}

// Component to display live countdown timer for a section
function SectionCountdownTimer({ minimumTimeSeconds, timeSpentSeconds, isActive, isCompleted }) {
  const { formattedTime, isTimeMet, isExpired } = useCountdownTimer({
    minimumTimeSeconds,
    timeSpentSeconds,
    isActive,
    isCompleted
  });

  if (!minimumTimeSeconds || minimumTimeSeconds <= 0) {
    return null;
  }

  if (isTimeMet) {
    return <span style={{ fontSize: "10px", color: "var(--success)", fontWeight: 400, flexShrink: 0 }}>
      ⏱ {formattedTime} ✓
    </span>;
  }

  return <span style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 400, flexShrink: 0 }}>
    ⏱ {formattedTime}
  </span>;
}

export function CourseSidebar({ course, activeModule, onSelectModule, progressData, onExit, refreshTrigger, courseProgress, sectionProgress: propSectionProgress }) {
  const [lockedModules, setLockedModules] = useState({});
  const [lockedSections, setLockedSections] = useState({});
  const [validating, setValidating] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});
  const [localSectionProgress, setLocalSectionProgress] = useState({});
  const validationAbortControllerRef = useRef(null);
  const validatingModuleIdsRef = useRef(new Set());

  // Use propSectionProgress if provided (from parent for synchronization), otherwise use local state
  const sectionProgress = propSectionProgress || localSectionProgress;

  const sections = course?.sections || [];
  
  // Memoize modules to prevent infinite re-renders
  // Only recompute when sections or course.modules_json actually change
  const modules = useMemo(() => {
    if (!course) return [];
    return sections.length > 0 
      ? sections.flatMap(s => s.modules || [])
      : (course.modules_json || []);
  }, [sections, course?.modules_json, course]);

  // Calculate section locking based on sequential progression
  // A section is locked if the previous section is not completed (including time requirement)
  // EXCEPTION: If course is completed/submitted, all sections are unlocked
  const sectionLocking = useMemo(() => {
    const locked = {};
    const isCourseCompleted = courseProgress?.status === "completed" || courseProgress?.status === "submitted";
// If course is completed, unlock all sections
    if (isCourseCompleted) {
      sections.forEach(section => {
        locked[section.id] = false;
      });
      return locked;
    }
    
    // Otherwise, apply sequential locking logic
    sections.forEach((section, index) => {
      // First section is always unlocked
      if (index === 0) {
        locked[section.id] = false;
        return;
      }
      
      // Check if previous section is completed
      const previousSection = sections[index - 1];
      if (!previousSection) {
        locked[section.id] = false;
        return;
      }
      
      // Check if previous section progress status is "completed"
      // This includes both module completion AND minimum time requirement
      // Handle both string and numeric IDs for compatibility
      const previousSectionProgress = sectionProgress[previousSection.id] || sectionProgress[String(previousSection.id)];
      const isPreviousCompleted = previousSectionProgress?.status === "completed";
// Section is locked if previous section is not completed
      // NO FALLBACK - must use section progress with time requirement validation
      locked[section.id] = !isPreviousCompleted;
    });
    return locked;
  }, [sections, sectionProgress, progressData, courseProgress]);

  // Validate module access when course or modules change
  useEffect(() => {
    async function validateAccess() {
      if (!modules.length) return;
      
      // Cancel any ongoing validation
      if (validationAbortControllerRef.current) {
        validationAbortControllerRef.current.abort();
      }
      
      validationAbortControllerRef.current = new AbortController();
      const { signal } = validationAbortControllerRef.current;
      
      setValidating(true);
      const locked = {};
      const newValidatingIds = new Set();
      
      for (const mod of modules) {
        // Skip if already validating this module (deduplication)
        if (validatingModuleIdsRef.current.has(mod.id)) {
          continue;
        }
        
        newValidatingIds.add(mod.id);
        
        try {
          const response = await api.post("/api/v1/learner/validate-access", {
            target_type: "module",
            target_id: mod.id
          }, { signal });
          locked[mod.id] = !response.data.allowed;
        } catch (e) {
          // If validation fails or is aborted, assume unlocked to avoid blocking access
          if (e.name !== 'AbortError') {
            locked[mod.id] = false;
          }
        }
      }
      
      validatingModuleIdsRef.current = newValidatingIds;
      
      // Only update state if not aborted
      if (!signal.aborted) {
        setLockedModules(locked);
        setValidating(false);
      }
    }
    
    validateAccess();
    
    // Cleanup: abort requests on unmount
    return () => {
      if (validationAbortControllerRef.current) {
        validationAbortControllerRef.current.abort();
      }
    };
  }, [course?.id, modules]);

  // Auto-expand sections containing the active module
  useEffect(() => {
    if (activeModule && sections.length > 0) {
      const newExpanded = {};
      sections.forEach(section => {
        const hasActiveModule = section.modules?.some(m => m.id === activeModule.id);
        if (hasActiveModule) {
          newExpanded[section.id] = true;
        }
      });
      setExpandedSections(newExpanded);
    }
  }, [activeModule, sections]);

  // Load section progress
  useEffect(() => {
    async function loadSectionProgress() {
      if (!course?.id) return;
      try {
        const { data } = await api.get(`/api/v1/learner/courses/${course.id}/section-progress`);
        setLocalSectionProgress(data || {});
      } catch (err) {
        console.error("Failed to load section progress", err);
      }
    }
    loadSectionProgress();

    // Refresh section progress every 30 seconds to update time spent
    const interval = setInterval(loadSectionProgress, 30000);
    return () => clearInterval(interval);
  }, [course?.id]);

  // Refresh section progress when refreshTrigger changes (after heartbeat updates time)
  useEffect(() => {
    if (refreshTrigger && course?.id) {
      async function loadSectionProgress() {
        try {
          const { data } = await api.get(`/api/v1/learner/courses/${course.id}/section-progress`);

          setLocalSectionProgress(data || {});
        } catch (err) {
          console.error("Failed to refresh section progress", err);
        }
      }
      loadSectionProgress();
    }
  }, [refreshTrigger, course?.id]);

  const toggleSection = (sectionId) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

  // Count completed modules
  const completedCount = Object.values(progressData).filter(status => status === "completed").length;
  const totalCount = modules.length || 1;
  const progressPercent = Math.round((completedCount / totalCount) * 100);

  return (
    <>
      <style>{`
        .course-sidebar {
          width: 300px;
          border-right: 1px solid var(--border-subtle);
          background: var(--surface-bg);
          display: flex;
          flex-direction: column;
          height: 100%;
        }
        
        @media (max-width: 767px) {
          .course-sidebar {
            width: 280px !important;
            max-width: 85vw !important;
          }
          
          .course-sidebar button {
            min-height: 44px !important;
            min-width: 44px !important;
          }
          
          .course-sidebar .module-title {
            white-space: normal !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
          }
          
          .course-sidebar .section-title {
            white-space: normal !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
          }
        }
        
        @media (max-width: 480px) {
          .course-sidebar {
            width: 260px !important;
            max-width: 90vw !important;
          }
        }
        
        @media (max-width: 375px) {
          .course-sidebar {
            width: 240px !important;
            max-width: 95vw !important;
          }
        }
      `}</style>
      <div data-lenis-prevent className="course-sidebar" style={{ width: "300px", borderRight: "1px solid var(--border-subtle)", background: "var(--surface-bg)", display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
        <button onClick={onExit} style={{ background: "transparent", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", padding: "8px", borderRadius: "4px", minWidth: "44px", minHeight: "44px" }} title="Exit Course">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
        </button>
        <div style={{ fontWeight: 600, fontSize: "16px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, minWidth: 0 }} className="section-title">
          {course.name}
        </div>
      </div>

      {/* Progress Summary */}
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>
            COURSE PROGRESS
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>
            {completedCount}/{modules.length} modules · {progressPercent}%
          </div>
        </div>
        <div className="progress-track" style={{ height: "6px", background: "var(--border-subtle)", borderRadius: "3px", overflow: "hidden" }}>
          <div 
            className="progress-fill" 
            style={{ 
              width: `${progressPercent}%`,
              background: "var(--primary)", 
              height: "100%",
              transition: "width 0.3s ease"
            }} 
          />
        </div>
      </div>

      {/* Module List */}
      <div data-lenis-prevent style={{ flex: 1, overflowY: "auto", padding: "12px 0" }}>
        {sections.length > 0 ? (
          // Section-based rendering
          sections.map((section, sectionIndex) => {
            const sectionModules = section.modules || [];
            if (sectionModules.length === 0) return null;
            
            const isExpanded = expandedSections[section.id] !== false;
            const isSectionLocked = sectionLocking[section.id];
            
            return (
              <div key={section.id}>
                {/* Section Header */}
                <button
                  onClick={() => !isSectionLocked && toggleSection(section.id)}
                  disabled={isSectionLocked}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    width: "100%",
                    padding: "12px 16px",
                    border: "none",
                    background: "var(--surface-subtle)",
                    cursor: isSectionLocked ? "not-allowed" : "pointer",
                    textAlign: "left",
                    gap: "8px",
                    fontWeight: 600,
                    fontSize: "13px",
                    color: isSectionLocked ? "var(--text-muted)" : "var(--text-primary)",
                    borderBottom: "1px solid var(--border-subtle)",
                    minHeight: "44px",
                    opacity: isSectionLocked ? 0.5 : 1
                  }}
                  title={isSectionLocked ? "Complete previous section to unlock" : section.title}
                >
                  <span style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s", flexShrink: 0 }}>
                    ▶
                  </span>
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 0 }} className="section-title">{section.title}</span>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 400, flexShrink: 0 }}>
                    {sectionModules.length}
                  </span>
                  <SectionCountdownTimer
                    minimumTimeSeconds={section.minimum_time_seconds}
                    timeSpentSeconds={sectionProgress[String(section.id)]?.time_spent_seconds || sectionProgress[section.id]?.time_spent_seconds || 0}
                    isActive={!isSectionLocked}
                    isCompleted={sectionProgress[String(section.id)]?.status === "completed" || sectionProgress[section.id]?.status === "completed"}
                  />
                  {isSectionLocked && (
                    <span style={{ color: "var(--warning)", fontSize: "11px", fontWeight: 500 }}>
                      🔒
                    </span>
                  )}
                </button>
                
                {/* Section Modules */}
                {isExpanded && !isSectionLocked && sectionModules.map((mod, index) => {
                  const isActive = activeModule?.id === mod.id;
                  const isCompleted = progressData[mod.id] === "completed";
                  const isLocked = lockedModules[mod.id] && !isCompleted;
                  const blockCount = Array.isArray(mod.content) ? mod.content.length : 0;
                  
                  return (
                    <button
                      key={mod.id}
                      onClick={() => !isLocked && onSelectModule(mod)}
                      disabled={isLocked}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        width: "100%",
                        padding: "12px 16px 12px 40px",
                        border: "none",
                        background: isActive ? "var(--surface-raised)" : "transparent",
                        borderLeft: isActive ? "3px solid var(--primary)" : "3px solid transparent",
                        cursor: isLocked ? "not-allowed" : "pointer",
                        textAlign: "left",
                        gap: "12px",
                        transition: "background 0.2s",
                        opacity: isLocked ? 0.5 : 1
                      }}
                      title={isLocked ? "Complete previous module to unlock" : mod.title}
                    >
                      <div style={{ 
                        width: "24px", 
                        height: "24px", 
                        borderRadius: "50%", 
                        border: isCompleted ? "none" : "1px solid var(--border-strong)",
                        background: isCompleted ? "var(--success)" : isLocked ? "var(--warning)" : "transparent",
                        color: isCompleted ? "var(--text-inverse)" : "var(--text-muted)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "12px",
                        flexShrink: 0
                      }}>
                        {isLocked ? "🔒" : isCompleted ? "✓" : index + 1}
                      </div>
                      <div style={{ flex: 1, overflow: "hidden", minWidth: 0 }}>
                        <div style={{ 
                          fontWeight: isActive ? 600 : 500, 
                          color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                          fontSize: "14px",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis"
                        }} className="module-title">
                          {mod.title}
                        </div>
                        <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px", display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{ textTransform: "capitalize" }}>{mod.module_type || "Lesson"}</span>
                          {blockCount > 0 && (
                            <span style={{ background: "var(--border-subtle)", borderRadius: "8px", padding: "0 6px", fontSize: "11px", fontWeight: 500 }}>
                              {blockCount} {blockCount === 1 ? "block" : "blocks"}
                            </span>
                          )}
                          {isLocked && (
                            <span style={{ color: "var(--warning)", fontSize: "11px", fontWeight: 500 }}>
                              Locked
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            );
          })
        ) : (
          // Fallback: flat module list (for backward compatibility)
          modules.map((mod, index) => {
            const isActive = activeModule?.id === mod.id;
            const isCompleted = progressData[mod.id] === "completed";
            const isLocked = lockedModules[mod.id] && !isCompleted;
            const blockCount = Array.isArray(mod.content) ? mod.content.length : 0;
            
            return (
              <button
                key={mod.id}
                onClick={() => !isLocked && onSelectModule(mod)}
                disabled={isLocked}
                style={{
                  display: "flex",
                  alignItems: "center",
                  width: "100%",
                  padding: "12px 16px",
                  border: "none",
                  background: isActive ? "var(--surface-raised)" : "transparent",
                  borderLeft: isActive ? "3px solid var(--primary)" : "3px solid transparent",
                  cursor: isLocked ? "not-allowed" : "pointer",
                  textAlign: "left",
                  gap: "12px",
                  transition: "background 0.2s",
                  opacity: isLocked ? 0.5 : 1,
                  minHeight: "44px"
                }}
                title={isLocked ? "Complete previous module to unlock" : mod.title}
              >
                <div style={{ 
                  width: "24px", 
                  height: "24px", 
                  borderRadius: "50%", 
                  border: isCompleted ? "none" : "1px solid var(--border-strong)",
                  background: isCompleted ? "var(--success)" : isLocked ? "var(--warning)" : "transparent",
                  color: isCompleted ? "var(--text-inverse)" : "var(--text-muted)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "12px",
                  flexShrink: 0
                }}>
                  {isLocked ? "🔒" : isCompleted ? "✓" : index + 1}
                </div>
                <div style={{ flex: 1, overflow: "hidden", minWidth: 0 }}>
                  <div style={{ 
                    fontWeight: isActive ? 600 : 500, 
                    color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                    fontSize: "14px",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis"
                  }} className="module-title">
                    {mod.title}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ textTransform: "capitalize" }}>{mod.module_type || "Lesson"}</span>
                    {blockCount > 0 && (
                      <span style={{ background: "var(--border-subtle)", borderRadius: "8px", padding: "0 6px", fontSize: "11px", fontWeight: 500 }}>
                        {blockCount} {blockCount === 1 ? "block" : "blocks"}
                      </span>
                    )}
                    {isLocked && (
                      <span style={{ color: "var(--warning)", fontSize: "11px", fontWeight: 500 }}>
                        Locked
                      </span>
                    )}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
    </>
  );
}
