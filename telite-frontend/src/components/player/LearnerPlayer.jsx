import React, { useEffect, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, EmptyState, LoadingState, ErrorState, Icon, useToast } from "../common/ui";
import { CourseSidebar } from "./CourseSidebar";
import { BlockRenderer } from "./BlockRenderer";
import { api, endLearningSession, heartbeatLearningSession, startLearningSession } from "../../services/client";

export function LearnerPlayer({ courseId, onExit, onCertificateIssued }) {
  const { showToast } = useToast();
  const scrollRef = useRef(null);
  const [courseData, setCourseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeModule, setActiveModule] = useState(null);
  const [progressData, setProgressData] = useState({});
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [courseProgress, setCourseProgress] = useState(null);
  const [submittingCourse, setSubmittingCourse] = useState(false);
  const [certificate, setCertificate] = useState(null);
  const [showCompletionSuccess, setShowCompletionSuccess] = useState(false);
  const [sectionProgressRefreshTrigger, setSectionProgressRefreshTrigger] = useState(0);
  const [sectionProgress, setSectionProgress] = useState({});

  useEffect(() => {
    async function loadCourse() {
      try {
        const { data } = await api.get(`/api/v1/learner/courses/${courseId}`);
        setCourseData(data);
        setCourseProgress(data.progress || null);

        // Load persisted module progress from backend
        try {
          const { data: moduleProgressData } = await api.get(`/api/v1/learner/courses/${courseId}/module-progress`);
          setProgressData(moduleProgressData || {});
        } catch (progressErr) {
          console.error("Failed to load module progress", progressErr);
          setProgressData({});
        }

        // Load section progress
        try {
          const { data: sectionProgressData } = await api.get(`/api/v1/learner/courses/${courseId}/section-progress`);
          setSectionProgress(sectionProgressData || {});
        } catch (sectionProgressErr) {
          console.error("Failed to load section progress", sectionProgressErr);
          setSectionProgress({});
        }

        // Get resume state - backend now returns first incomplete module sequentially
        try {
          const { data: resumeData } = await api.get(`/api/v1/learner/resume/${courseId}`);
          // Find the module to activate based on sequential progression
          if (resumeData.last_module_id && data.modules_json) {
            const mod = data.modules_json.find(m => m.id === resumeData.last_module_id);
            if (mod) setActiveModule(mod);
            else if (data.modules_json.length > 0) setActiveModule(data.modules_json[0]);
          } else if (data.modules_json && data.modules_json.length > 0) {
            setActiveModule(data.modules_json[0]);
          }
        } catch {
          if (data.modules_json && data.modules_json.length > 0) {
            setActiveModule(data.modules_json[0]);
          }
        }
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || "Failed to load course details");
      } finally {
        setLoading(false);
      }
    }
    loadCourse();
  }, [courseId]);

  useEffect(() => {
    if (!courseId) return undefined;
    let cancelled = false;
    let sessionId = null;
    let lastActiveAt = Date.now();
    let accumulatedSeconds = 0;
    let lastTickAt = Date.now();

    const markActive = () => {
      lastActiveAt = Date.now();
    };
    const isActivelyLearning = () => (
      document.visibilityState === "visible"
      && document.hasFocus()
      && Date.now() - lastActiveAt <= 120000
    );
    const flush = async () => {
      if (!sessionId || accumulatedSeconds <= 0) return;
      const seconds = Math.min(accumulatedSeconds, 90);
      accumulatedSeconds -= seconds;
      try {
        await heartbeatLearningSession({
          session_id: sessionId,
          course_id: courseId,
          module_id: activeModule?.id || null,
          active_seconds: seconds,
        });
        // Trigger section progress refresh to check if minimum time requirement was met
        setSectionProgressRefreshTrigger(prev => prev + 1);
      } catch {
        accumulatedSeconds += seconds;
      }
    };

    startLearningSession({ course_id: courseId, module_id: activeModule?.id || null })
      .then((data) => {
        if (!cancelled) sessionId = data?.session?.id;
      })
      .catch(() => {});

    const tick = setInterval(() => {
      const now = Date.now();
      const delta = Math.max(0, Math.round((now - lastTickAt) / 1000));
      lastTickAt = now;
      if (isActivelyLearning()) {
        accumulatedSeconds += Math.min(delta, 15);
      }
    }, 5000);
    const heartbeat = setInterval(() => {
      flush();
    }, 30000);

    const end = (reason = "ended") => {
      cancelled = true;
      clearInterval(tick);
      clearInterval(heartbeat);
      const pending = Math.min(accumulatedSeconds, 90);
      if (sessionId && pending > 0 && navigator.sendBeacon) {
        const payload = JSON.stringify({
          session_id: sessionId,
          course_id: courseId,
          module_id: activeModule?.id || null,
          active_seconds: pending,
        });
        navigator.sendBeacon("/api/v1/learner/learning-sessions/heartbeat", new Blob([payload], { type: "application/json" }));
      } else {
        flush();
      }
      if (sessionId) {
        endLearningSession({ session_id: sessionId, reason }).catch(() => {});
      }
    };

    ["mousemove", "keydown", "scroll", "click", "touchstart"].forEach((eventName) => window.addEventListener(eventName, markActive, { passive: true }));
    const handleBeforeUnload = () => end("browser_closed");
    window.addEventListener("beforeunload", handleBeforeUnload);
    document.addEventListener("visibilitychange", markActive);

    return () => {
      ["mousemove", "keydown", "scroll", "click", "touchstart"].forEach((eventName) => window.removeEventListener(eventName, markActive));
      window.removeEventListener("beforeunload", handleBeforeUnload);
      document.removeEventListener("visibilitychange", markActive);
      end("module_changed");
    };
  }, [courseId, activeModule?.id]);

  useEffect(() => {
    // Emit MODULE_STARTED
    if (activeModule && courseId) {
      // Prevent duplicate starts if already completed or tracked recently? 
      // The backend can handle deduplication or we just blindly send it.
      api.post("/api/v1/learner/events", {
          events: [
            {
              event_type: "MODULE_STARTED",
              course_id: courseId,
              module_id: activeModule.id
            },
            {
              event_type: "MODULE_VIEWED",
              course_id: courseId,
              module_id: activeModule.id
            }
          ]
      }).catch(() => {});
    }
  }, [activeModule?.id, courseId]);

  // Refresh section progress periodically to update time spent
  useEffect(() => {
    if (!courseId) return undefined;
    const interval = setInterval(async () => {
      try {
        const { data: sectionProgressData } = await api.get(`/api/v1/learner/courses/${courseId}/section-progress`);
        setSectionProgress(sectionProgressData || {});
      } catch (err) {
        console.error("Failed to refresh section progress", err);
      }
    }, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [courseId]);
  // Check if current section's minimum time requirement is met
  const isSectionTimeRequirementMet = () => {
    if (!activeModule || !courseData?.sections) return true;
    
    // Find the section containing the current module
    const currentSection = courseData.sections.find(section => 
      section.modules?.some(mod => mod.id === activeModule.id)
    );
    
    if (!currentSection || !currentSection.minimum_time_seconds || currentSection.minimum_time_seconds <= 0) {
      return true; // No time requirement
    }
    
    // Check if time spent meets requirement
    const sectionProgressData = sectionProgress[String(currentSection.id)] || sectionProgress[currentSection.id];
    const timeSpent = sectionProgressData?.time_spent_seconds || 0;
    
    return timeSpent >= currentSection.minimum_time_seconds;
  };

  const handleModuleComplete = async () => {
    if (!activeModule) return;
    
    // Check if section time requirement is met
    if (!isSectionTimeRequirementMet()) {
      const currentSection = courseData.sections.find(section => 
        section.modules?.some(mod => mod.id === activeModule.id)
      );
      const timeSpent = sectionProgress[String(currentSection.id)]?.time_spent_seconds || sectionProgress[currentSection.id]?.time_spent_seconds || 0;
      const remaining = currentSection.minimum_time_seconds - timeSpent;
      showToast(`Please spend at least ${Math.ceil(remaining / 60)} more minutes in this section before completing.`, "error");
      return;
    }
    
    try {
      await api.post("/api/v1/learner/progress", {
        course_id: courseId,
        module_updates: [{ module_id: activeModule.id, status: "completed" }]
      });
      // Update local progress state
      setProgressData(prev => ({ ...prev, [activeModule.id]: "completed" }));
      // Trigger section progress refresh to check if section should be completed
      setSectionProgressRefreshTrigger(prev => prev + 1);
      showToast("Module marked complete.", "success");
      
      // Auto-advance to next module using sequential progression
      // Find current module in sections structure
      let nextModule = null;
      for (const section of courseData.sections || []) {
        const sectionModules = section.modules || [];
        const currentIndex = sectionModules.findIndex(m => m.id === activeModule.id);
        
        if (currentIndex >= 0) {
          // Found current module, check if next module exists in same section
          if (currentIndex < sectionModules.length - 1) {
            nextModule = sectionModules[currentIndex + 1];
          } else {
            // No more modules in this section, find first module of next section
            const currentSectionIndex = courseData.sections.findIndex(s => s.id === section.id);
            if (currentSectionIndex < courseData.sections.length - 1) {
              const nextSection = courseData.sections[currentSectionIndex + 1];
              if (nextSection.modules && nextSection.modules.length > 0) {
                nextModule = nextSection.modules[0];
              }
            }
          }
          break;
        }
      }
      
      if (nextModule) {
        setActiveModule(nextModule);
      }
    } catch (e) {
      console.error("Failed to update progress", e);
      showToast("Unable to update progress.", "error");
    }
  };

  const handleSubmitCourse = async () => {
    if (!courseId) return;
    setSubmittingCourse(true);
    try {
      // First, mark the last module as complete if not already completed
      if (activeModule && progressData[activeModule.id] !== "completed") {
        await api.post("/api/v1/learner/progress", {
          course_id: courseId,
          module_updates: [{ module_id: activeModule.id, status: "completed" }]
        });
        // Update local progress state
        setProgressData(prev => ({ ...prev, [activeModule.id]: "completed" }));
      }

      // Submit the course (this validates completion and auto-generates certificate)
      const response = await api.post(`/api/v1/learner/courses/${courseId}/submit`);
      const submissionData = response.data;
      
      // Certificate is returned in the submission response
      if (submissionData.certificate) {
        setCertificate(submissionData.certificate);
      } else if (submissionData.already_submitted) {
        // Already submitted, certificate should be in response
        if (submissionData.certificate) {
          setCertificate(submissionData.certificate);
        } else {
          console.warn("No certificate in response for already submitted course");
        }
      } else {
        console.warn("No certificate in submission response");
      }
      
      // Update course progress status to trigger section unlocking
      setCourseProgress(prev => ({ ...prev, status: "submitted" }));
      
      // Notify parent component that certificate was issued (to refresh dashboard)
      if (onCertificateIssued && submissionData.certificate) {
        onCertificateIssued();
      }
      
      setShowCompletionSuccess(true);
      showToast("Congratulations! Course submitted successfully.", "success");
    } catch (e) {
      console.error("Failed to submit course", e);
      const errorMsg = e?.response?.data?.detail || e?.message || "Unable to submit course";
      showToast(errorMsg, "error");
    } finally {
      setSubmittingCourse(false);
    }
  };

  const handleViewCertificate = () => {
    if (certificate?.verification_token) {
      window.open(`/public/verify/${certificate.verification_token}`, "_blank");
    } else {
      console.warn("Certificate or verification_token not available");
    }
  };

  const handleDownloadCertificate = async () => {
    if (certificate?.verification_token) {
      try {
        // Use the new download endpoint
        const response = await api.get(`/api/certificates/${courseId}/download`, {
          responseType: 'blob'
        });
        
        // Create a blob URL and trigger download
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `certificate_${courseId}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error("Failed to download certificate", error);
        // Fallback to verification page
        window.open(`/public/verify/${certificate.verification_token}`, "_blank");
      }
    } else {
      console.warn("Certificate or verification_token not available");
    }
  };

  const isLastModule = () => {
    if (!activeModule || !courseData?.sections) return false;
    // Check if this is the last module in the last section
    const lastSection = courseData.sections[courseData.sections.length - 1];
    if (!lastSection.modules || lastSection.modules.length === 0) return false;
    const lastModule = lastSection.modules[lastSection.modules.length - 1];
    return activeModule.id === lastModule.id;
  };

  const isCourseComplete = () => {
    return courseProgress?.status === "submitted" || courseProgress?.status === "completed";
  };

  const canSubmitCourse = () => {
    if (!courseData?.sections) return false;
    
    // Check if all modules are completed
    let totalModules = 0;
    let completedModules = 0;
    
    for (const section of courseData.sections) {
      const sectionModules = section.modules || [];
      totalModules += sectionModules.length;
      for (const module of sectionModules) {
        if (progressData[module.id] === "completed") {
          completedModules += 1;
        }
      }
    }
    
    return totalModules > 0 && completedModules === totalModules;
  };

  const handleModuleSelect = (module) => {
    setActiveModule(module);
    setSidebarOpen(false); // Auto-close sidebar on mobile after selection
  };

  const canScrollVertically = (element, deltaY) => {
    if (!element || !(element instanceof HTMLElement)) return false;
    const style = window.getComputedStyle(element);
    if (!["auto", "scroll"].includes(style.overflowY)) return false;
    if (element.scrollHeight <= element.clientHeight + 1) return false;
    if (deltaY < 0) return element.scrollTop > 0;
    if (deltaY > 0) return element.scrollTop + element.clientHeight < element.scrollHeight - 1;
    return false;
  };

  const nestedScrollableOwnsWheel = (target, root, deltaY) => {
    let node = target;
    while (node && node !== root) {
      if (canScrollVertically(node, deltaY)) return true;
      node = node.parentElement;
    }
    return false;
  };

  const handleLessonWheel = (event) => {
    const root = scrollRef.current;
    if (!root || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    if (nestedScrollableOwnsWheel(event.target, root, event.deltaY)) return;
    if (!canScrollVertically(root, event.deltaY)) return;
    event.preventDefault();
    root.scrollTop += event.deltaY;
  };

  useEffect(() => {
    const root = scrollRef.current;
    if (!root) return undefined;
    root.addEventListener("wheel", handleLessonWheel, { capture: true, passive: false });
    return () => root.removeEventListener("wheel", handleLessonWheel, { capture: true });
  });

  if (loading) return <LoadingState title="Loading course player..." />;
  if (error) return <ErrorState body={error} action={<Button onClick={onExit}>Back to Dashboard</Button>} />;

  return (
    <>
      <style>{`
        html, body {
          -webkit-user-select: text;
          user-select: text;
        }

        * {
          box-sizing: border-box;
        }

        .learner-player {
          scroll-behavior: auto;
          pointer-events: auto;
          touch-action: auto;
        }
        
        .lesson-scroll-region {
          scroll-behavior: auto;
          -webkit-overflow-scrolling: touch;
          overscroll-behavior-y: auto;
          pointer-events: auto;
          touch-action: pan-y;
          will-change: scroll-position;
          min-height: 0;
        }

        .lesson-scroll-region > div {
          pointer-events: auto;
        }
        
        @media (max-width: 767px) {
          .mobile-menu-toggle {
            display: flex !important;
          }
          
          .course-sidebar-container {
            position: fixed !important;
            left: -300px !important;
            top: 0 !important;
            z-index: 9999 !important;
            transition: left 0.3s ease !important;
            box-shadow: 2px 0 15px rgba(0,0,0,0.1) !important;
          }
          
          .course-sidebar-container.mobile-open {
            left: 0 !important;
          }
          
          .player-main {
            width: 100% !important;
          }
          
          .learner-player {
            overflow-x: hidden !important;
          }
          
          .lesson-scroll-region {
            padding: 20px 16px !important;
          }
          
          .lesson-scroll-region > div {
            max-width: 100% !important;
          }
        }
        
        @media (min-width: 768px) {
          .course-sidebar-container {
            position: relative !important;
            left: auto !important;
          }
        }
      `}</style>
      <div className="learner-player" style={{ display: "flex", height: "100vh", background: "var(--surface-bg)", color: "var(--text-primary)", width: "100%", zIndex: 10000, overflow: "hidden" }}>
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          onClick={() => setSidebarOpen(false)}
          style={{ 
            position: "fixed", 
            top: 0, 
            left: 0, 
            right: 0, 
            bottom: 0, 
            background: "rgba(0,0,0,0.5)", 
            zIndex: 9998
          }}
        />
      )}

      {/* Sidebar Navigation — fixed height, internal scroll */}
      <div 
        style={{
          flexShrink: 0,
          width: "300px",
          height: "100%",
          overflowY: "auto",
          position: "relative",
          background: "var(--surface-bg)"
        }}
        className={`course-sidebar-container ${sidebarOpen ? 'mobile-open' : ''}`}
      >
        <CourseSidebar 
          course={courseData} 
          activeModule={activeModule} 
          onSelectModule={handleModuleSelect}
          progressData={progressData}
          onExit={onExit}
          refreshTrigger={sectionProgressRefreshTrigger}
          courseProgress={courseProgress}
        />
      </div>

      {/* Main Content Area — single scroll region */}
      <div className="player-main" style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", color: "var(--text-primary)" }}>
        {/* Sticky Header */}
        <header style={{ flexShrink: 0, padding: "16px 24px", borderBottom: "1px solid var(--border-subtle)", background: "var(--surface-raised)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flex: 1, minWidth: 0 }}>
            {/* Hamburger Menu Button - Mobile Only */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="mobile-menu-toggle"
              style={{
                display: "none",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                width: "44px",
                height: "44px",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: "8px",
                borderRadius: "4px",
                flexShrink: 0
              }}
              aria-label="Toggle sidebar"
            >
              <span style={{
                display: "block",
                width: "20px",
                height: "2px",
                background: "var(--text-primary)",
                marginBottom: "4px",
                borderRadius: "1px"
              }} />
              <span style={{
                display: "block",
                width: "20px",
                height: "2px",
                background: "var(--text-primary)",
                marginBottom: "4px",
                borderRadius: "1px"
              }} />
              <span style={{
                display: "block",
                width: "20px",
                height: "2px",
                background: "var(--text-primary)",
                borderRadius: "1px"
              }} />
            </button>
            <h2 style={{ margin: 0, fontSize: "20px", fontWeight: "600", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{activeModule?.title || courseData.name}</h2>
          </div>
          {canSubmitCourse() ? (
            <Button 
              tone="primary" 
              onClick={handleSubmitCourse}
              disabled={submittingCourse}
            >
              {submittingCourse ? "Submitting..." : "Submit Course"}
            </Button>
          ) : (
            <Button 
              tone="primary" 
              onClick={handleModuleComplete}
              disabled={!isSectionTimeRequirementMet()}
            >
              {!isSectionTimeRequirementMet() ? "Wait for timer..." : "Mark Complete"}
            </Button>
          )}
        </header>

        {/* Scrollable Content */}
        <div
          ref={scrollRef}
          className="lesson-scroll-region"
          style={{ flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden", padding: "40px", display: "flex", justifyContent: "center", WebkitOverflowScrolling: "touch", overscrollBehaviorY: "auto", touchAction: "pan-y" }}
        >
          <div style={{ maxWidth: "800px", width: "100%" }}>
            {showCompletionSuccess ? (
              <div style={{ textAlign: "center", padding: "60px 20px" }}>
                <div style={{ fontSize: "64px", marginBottom: "24px" }}>🎉</div>
                <h1 style={{ fontSize: "32px", fontWeight: "700", marginBottom: "16px", color: "var(--text-primary)" }}>
                  Congratulations!
                </h1>
                <p style={{ fontSize: "18px", color: "var(--text-secondary)", marginBottom: "32px" }}>
                  You have successfully completed this course.
                </p>
                <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
                  {certificate?.verification_token ? (
                    <>
                      <Button tone="primary" onClick={handleViewCertificate}>
                        View Certificate
                      </Button>
                      <Button tone="neutral" onClick={handleDownloadCertificate}>
                        Download Certificate
                      </Button>
                    </>
                  ) : (
                    <Button tone="neutral" disabled>
                      Certificate Loading...
                    </Button>
                  )}
                  <Button tone="ghost" onClick={onExit}>
                    Back to Dashboard
                  </Button>
                </div>
              </div>
            ) : activeModule && activeModule.content?.length > 0 ? (
              <BlockRenderer content={activeModule.content} courseId={courseId} moduleId={activeModule.id} />
            ) : activeModule ? (
              <EmptyState title="No lesson content" body="This module does not have learner-visible blocks yet." />
            ) : (
              <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)", fontSize: "16px" }}>
                Select a module to begin
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
    </>
  );
}
