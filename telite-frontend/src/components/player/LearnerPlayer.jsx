import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, EmptyState, LoadingState, ErrorState, Icon, useToast } from "../common/ui";
import { CourseSidebar } from "./CourseSidebar";
import { BlockRenderer } from "./BlockRenderer";
import { api } from "../../services/client";

export function LearnerPlayer({ courseId, onExit }) {
  const { showToast } = useToast();
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
    // Heartbeat for time spent
    const interval = setInterval(() => {
      if (!courseId) return;
      api.post("/api/v1/learner/heartbeat", {
          course_id: courseId,
          module_id: activeModule?.id || null,
          time_spent_seconds: 15
      }).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, [courseId, activeModule]);

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

  const handleModuleComplete = async () => {
    if (!activeModule) return;
    try {
      await api.post("/api/v1/learner/progress", {
        course_id: courseId,
        module_updates: [{ module_id: activeModule.id, status: "completed" }]
      });
      // Update local progress state
      setProgressData(prev => ({ ...prev, [activeModule.id]: "completed" }));
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
        }
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

  if (loading) return <LoadingState title="Loading course player..." />;
  if (error) return <ErrorState body={error} action={<Button onClick={onExit}>Back to Dashboard</Button>} />;

  return (
    <>
      <style>{`
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
          
          .player-main > div:last-child {
            padding: 20px 16px !important;
          }
          
          .player-main > div:last-child > div {
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
            <Button tone="primary" onClick={handleModuleComplete}>Mark Complete</Button>
          )}
        </header>

        {/* Scrollable Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "40px", display: "flex", justifyContent: "center" }}>
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
                  <Button tone="primary" onClick={handleViewCertificate}>
                    View Certificate
                  </Button>
                  <Button tone="neutral" onClick={handleDownloadCertificate}>
                    Download Certificate
                  </Button>
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
