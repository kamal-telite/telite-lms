import React, { useEffect, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, EmptyState, LoadingState, ErrorState, Icon, useToast } from "../common/ui";
import { CourseSidebar } from "./CourseSidebar";
import { BlockRenderer } from "./BlockRenderer";
import { api, endLearningSession, heartbeatLearningSession, startLearningSession } from "../../services/client";
import { useCountdownTimer } from "../../hooks/useCountdownTimer";

function mergeSectionProgress(prev, incoming) {
  if (!incoming || typeof incoming !== "object") return prev || {};
  const merged = { ...incoming };
  for (const key of Object.keys(merged)) {
    const prevEntry = prev?.[key] ?? prev?.[String(key)];
    if (!prevEntry) continue;
    merged[key] = {
      ...merged[key],
      time_spent_seconds: Math.max(
        merged[key]?.time_spent_seconds || 0,
        prevEntry.time_spent_seconds || 0,
      ),
    };
  }
  return merged;
}

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
  const [markingModuleComplete, setMarkingModuleComplete] = useState(false);
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
          setSectionProgress((prev) => mergeSectionProgress(prev, sectionProgressData || {}));
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
            if (mod) {
              try {
                const validation = await api.post("/api/v1/learner/validate-access", {
                  target_type: "module",
                  target_id: mod.id,
                });
                if (validation.data.allowed) {
                  setActiveModule(mod);
                } else {
                  for (const candidate of data.modules_json) {
                    if (!candidate?.id) continue;
                    const candidateValidation = await api.post("/api/v1/learner/validate-access", {
                      target_type: "module",
                      target_id: candidate.id,
                    });
                    if (candidateValidation.data.allowed) {
                      setActiveModule(candidate);
                      break;
                    }
                  }
                }
              } catch {
                setActiveModule(mod);
              }
            } else if (data.modules_json.length > 0) {
              setActiveModule(data.modules_json[0]);
            }
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

  const sessionIdRef = useRef(null);
  const accumulatedSecondsRef = useRef(0);
  const flushRef = useRef(async () => {});

  const flush = async () => {
    const sessionId = sessionIdRef.current;
    const seconds = Math.min(accumulatedSecondsRef.current, 90);
    if (!sessionId || seconds <= 0) return;
    accumulatedSecondsRef.current -= seconds;
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
      accumulatedSecondsRef.current += seconds;
    }
  };

  useEffect(() => {
    flushRef.current = flush;
  }, [courseId, activeModule?.id]);

  useEffect(() => {
    if (!courseId) return undefined;
    let cancelled = false;
    let lastActiveAt = Date.now();
    let lastTickAt = Date.now();

    // Reset session tracking refs
    sessionIdRef.current = null;
    accumulatedSecondsRef.current = 0;

    const markActive = () => {
      lastActiveAt = Date.now();
    };
    const isActivelyLearning = () => (
      document.visibilityState === "visible"
      && document.hasFocus()
      && Date.now() - lastActiveAt <= 120000
    );

    startLearningSession({ course_id: courseId, module_id: activeModule?.id || null })
      .then((data) => {
        if (!cancelled) {
          sessionIdRef.current = data?.session?.id;
        }
      })
      .catch(() => {});

    const tick = setInterval(() => {
      const now = Date.now();
      const delta = Math.max(0, Math.round((now - lastTickAt) / 1000));
      lastTickAt = now;
      if (isActivelyLearning()) {
        accumulatedSecondsRef.current += Math.min(delta, 15);
      }
    }, 5000);
    const heartbeat = setInterval(() => {
      flushRef.current();
    }, 30000);

    const end = (reason = "ended") => {
      cancelled = true;
      clearInterval(tick);
      clearInterval(heartbeat);
      const pending = Math.min(accumulatedSecondsRef.current, 90);
      const sessionId = sessionIdRef.current;
      if (sessionId && pending > 0 && navigator.sendBeacon) {
        const payload = JSON.stringify({
          session_id: sessionId,
          course_id: courseId,
          module_id: activeModule?.id || null,
          active_seconds: pending,
        });
        navigator.sendBeacon("/api/v1/learner/learning-sessions/heartbeat", new Blob([payload], { type: "application/json" }));
      } else {
        flushRef.current();
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
        setSectionProgress((prev) => mergeSectionProgress(prev, sectionProgressData || {}));
      } catch (err) {
        console.error("Failed to refresh section progress", err);
      }
    }, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [courseId]);

  // Get current section data for countdown timer
  const getCurrentSection = () => {
    if (!activeModule || !courseData?.sections) return null;
    return courseData.sections.find(section => 
      section.modules?.some(mod => mod.id === activeModule.id)
    );
  };

  const currentSection = getCurrentSection();
  const currentSectionProgress = currentSection ? (sectionProgress[String(currentSection.id)] || sectionProgress[currentSection.id]) : null;
  const timeSpentSeconds = currentSectionProgress?.time_spent_seconds || 0;
  const minimumTimeSeconds = currentSection?.minimum_time_seconds || 0;
  const isSectionCompleted = currentSectionProgress?.status === "completed";

  // Use countdown timer hook
  const { formattedTime, isTimeMet, isExpired } = useCountdownTimer({
    minimumTimeSeconds,
    timeSpentSeconds,
    isActive: !!activeModule && !!currentSection,
    isCompleted: isSectionCompleted,
    resetKey: currentSection?.id ?? null,
  });

  // Check if current section's minimum time requirement is met
  const isSectionTimeRequirementMet = () => {
    if (!activeModule || !courseData?.sections) return true;
    if (!currentSection || !minimumTimeSeconds || minimumTimeSeconds <= 0) {
      return true; // No time requirement
    }
    if (isTimeMet) {
      return true;
    }
    return timeSpentSeconds >= minimumTimeSeconds;
  };

  const timerSyncedSectionRef = useRef(null);

  // Sync section time to backend when local countdown completes (heartbeats may lag behind UI)
  useEffect(() => {
    if (!isExpired || minimumTimeSeconds <= 0 || !currentSection) return;
    if (timerSyncedSectionRef.current === currentSection.id) return;
    timerSyncedSectionRef.current = currentSection.id;

    setSectionProgress((prev) => ({
      ...prev,
      [currentSection.id]: {
        ...(prev[currentSection.id] || prev[String(currentSection.id)] || {}),
        time_spent_seconds: minimumTimeSeconds,
        status: prev[currentSection.id]?.status || prev[String(currentSection.id)]?.status || "in_progress",
      },
    }));

    const syncProgress = async () => {
      try {
        await flushRef.current();

        const sectionId = currentSection.id;
        for (let attempt = 0; attempt < 4; attempt += 1) {
          const { data: sectionProgressData } = await api.get(
            `/api/v1/learner/courses/${courseId}/section-progress`,
          );
          const spent =
            sectionProgressData?.[sectionId]?.time_spent_seconds ??
            sectionProgressData?.[String(sectionId)]?.time_spent_seconds ??
            0;

          if (spent >= minimumTimeSeconds) {
            setSectionProgress((prev) => mergeSectionProgress(prev, sectionProgressData || {}));
            setSectionProgressRefreshTrigger((prev) => prev + 1);
            return;
          }

          const gap = minimumTimeSeconds - spent;
          const sessionId = sessionIdRef.current;
          if (gap > 0 && sessionId) {
            await heartbeatLearningSession({
              session_id: sessionId,
              course_id: courseId,
              module_id: activeModule?.id || null,
              active_seconds: Math.min(gap, 90),
            });
          } else {
            break;
          }
        }

        const { data: sectionProgressData } = await api.get(
          `/api/v1/learner/courses/${courseId}/section-progress`,
        );
        setSectionProgress((prev) => mergeSectionProgress(prev, sectionProgressData || {}));
        setSectionProgressRefreshTrigger((prev) => prev + 1);
      } catch (err) {
        console.error("Failed to sync progress on timer completion", err);
      }
    };

    syncProgress();
  }, [isExpired, minimumTimeSeconds, courseId, currentSection?.id, activeModule?.id]);

  useEffect(() => {
    timerSyncedSectionRef.current = null;
  }, [currentSection?.id]);

  const handleModuleComplete = async () => {
    if (!activeModule || markingModuleComplete) return;
    
    // Check if section time requirement is met
    if (!isSectionTimeRequirementMet()) {
      const remaining = minimumTimeSeconds - timeSpentSeconds;
      showToast(`Please spend at least ${Math.ceil(remaining / 60)} more minutes in this section before completing.`, "error");
      return;
    }
    
    setMarkingModuleComplete(true);
    try {
      if (minimumTimeSeconds > 0 && timeSpentSeconds < minimumTimeSeconds && isTimeMet) {
        await flushRef.current();

        let remaining = minimumTimeSeconds - timeSpentSeconds;
        const sessionId = sessionIdRef.current;

        while (remaining > 0 && sessionId) {
          const sendSeconds = Math.min(remaining, 90);
          await heartbeatLearningSession({
            session_id: sessionId,
            course_id: courseId,
            module_id: activeModule.id,
            active_seconds: sendSeconds,
          });
          remaining -= sendSeconds;

          if (remaining > 0) {
            try {
              const { data: sectionProgressData } = await api.get(
                `/api/v1/learner/courses/${courseId}/section-progress`,
              );
              const spent =
                sectionProgressData?.[currentSection?.id]?.time_spent_seconds ??
                sectionProgressData?.[String(currentSection?.id)]?.time_spent_seconds ??
                0;
              if (spent >= minimumTimeSeconds) {
                break;
              }
              remaining = minimumTimeSeconds - spent;
            } catch (syncErr) {
              console.warn("Failed to refresh section progress while syncing time", syncErr);
              break;
            }
          }
        }
      }

      const { data: progressResponse } = await api.post("/api/v1/learner/progress", {
        course_id: courseId,
        module_updates: [{ module_id: activeModule.id, status: "completed" }]
      });

      const [moduleProgressResponse, sectionProgressResponse, courseResponse] = await Promise.all([
        api.get(`/api/v1/learner/courses/${courseId}/module-progress`),
        api.get(`/api/v1/learner/courses/${courseId}/section-progress`),
        api.get(`/api/v1/learner/courses/${courseId}`),
      ]);

      setProgressData(moduleProgressResponse.data || {});
      setSectionProgress((prev) => mergeSectionProgress(prev, sectionProgressResponse.data || {}));
      setCourseProgress(courseResponse.data?.progress || { status: progressResponse?.course_status || "in_progress" });
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
        const currentSectionId = currentSection?.id;
        const refreshedSectionProgress = sectionProgressResponse.data || {};
        const currentSectionProgressRefreshed = currentSectionId
          ? refreshedSectionProgress[String(currentSectionId)] || refreshedSectionProgress[currentSectionId]
          : null;
        const currentSectionCompleted = currentSectionProgressRefreshed?.status === "completed";
        const nextModuleInCurrentSection = currentSectionId && nextModule.section_id === currentSectionId;

        // Only auto-advance to the next section if the current section is completed and unlocked.
        if (nextModuleInCurrentSection || currentSectionCompleted) {
          try {
            const { data: validationData } = await api.post("/api/v1/learner/validate-access", {
              target_type: "module",
              target_id: nextModule.id,
            });
            if (validationData.allowed) {
              setActiveModule(nextModule);
            }
          } catch (validationError) {
            console.warn("Next module access validation failed", validationError);
          }
        }
      }
    } catch (e) {
      console.error("Failed to update progress", e);
      const errorMsg = e?.response?.data?.detail || e?.message || "Unable to update progress.";
      showToast(errorMsg, "error");
    } finally {
      setMarkingModuleComplete(false);
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
          scrollbar-width: none;
          -ms-overflow-style: none;
        }

        .lesson-scroll-region::-webkit-scrollbar {
          display: none;
        }

        .learner-player__header {
          position: sticky;
          top: 0;
          z-index: 10020;
          isolation: isolate;
        }

        .learner-player__timer {
          position: relative;
          z-index: 1;
          flex-shrink: 0;
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
            padding: 20px 16px 0 !important;
          }
          
          .lesson-scroll-region > div {
            max-width: 100% !important;
          }
          
          .content-spacer {
            height: 100px !important;
            width: 100% !important;
            flex-shrink: 0 !important;
          }
        }
        
        @media (min-width: 768px) {
          .course-sidebar-container {
            position: sticky !important;
            left: auto !important;
          }
        }
      `}</style>
      <div className="learner-player" style={{ position: "fixed", inset: 0, display: "flex", height: "100vh", background: "var(--surface-bg)", color: "var(--text-primary)", width: "100%", zIndex: 10000, overflow: "hidden" }}>
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
        data-lenis-prevent
        style={{
          flexShrink: 0,
          width: "300px",
          height: "100vh",
          overflowY: "auto",
          position: "sticky",
          top: 0,
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
          sectionProgress={sectionProgress}
          activeSectionTimer={{ formattedTime, isTimeMet }}
        />
      </div>

      {/* Main Content Area — single scroll region */}
      <div className="player-main" style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", minHeight: 0, overflow: "hidden", color: "var(--text-primary)" }}>
        {/* Sticky Header */}
        <header className="learner-player__header" style={{ flexShrink: 0, padding: "16px 24px", borderBottom: "1px solid var(--border-subtle)", background: "var(--surface-raised)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
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
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {/* Countdown Timer Display */}
            {minimumTimeSeconds > 0 && (
              <div className="learner-player__timer" style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: "6px",
                padding: "6px 12px",
                background: isTimeMet ? "var(--success-subtle)" : "var(--surface-subtle)",
                borderRadius: "6px",
                border: isTimeMet ? "1px solid var(--success)" : "1px solid var(--border-subtle)"
              }}>
                <span style={{ fontSize: "14px", color: isTimeMet ? "var(--success)" : "var(--text-muted)" }}>⏱</span>
                <span style={{ 
                  fontSize: "16px", 
                  fontWeight: "600", 
                  fontFamily: "monospace",
                  color: isTimeMet ? "var(--success)" : "var(--text-primary)" 
                }}>
                  {formattedTime}
                </span>
              </div>
            )}
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
                disabled={markingModuleComplete || !isSectionTimeRequirementMet()}
              >
                {markingModuleComplete ? "Marking..." : !isSectionTimeRequirementMet() ? "Wait for timer..." : "Mark Complete"}
              </Button>
            )}
          </div>
        </header>

        {/* Scrollable Content */}
        <div
          ref={scrollRef}
          className="lesson-scroll-region"
          style={{ flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden", padding: "40px 40px 0", display: "flex", flexDirection: "column", alignItems: "center", WebkitOverflowScrolling: "touch", overscrollBehaviorY: "contain", touchAction: "pan-y" }}
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
            <div className="content-spacer" style={{ height: "100px", width: "100%" }} aria-hidden="true" />
          </div>
        </div>
      </div>
    </div>
    </>
  );
}
