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

  useEffect(() => {
    async function loadCourse() {
      try {
        const { data } = await api.get(`/api/v1/learner/courses/${courseId}`);
        setCourseData(data);
        
        // Get resume state
        try {
          const { data: resumeData } = await api.get(`/api/v1/learner/resume/${courseId}`);
          // Find the module to activate
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
      
      // Auto-advance to next module
      const currentIndex = courseData.modules_json.findIndex(m => m.id === activeModule.id);
      if (currentIndex >= 0 && currentIndex < courseData.modules_json.length - 1) {
        setActiveModule(courseData.modules_json[currentIndex + 1]);
      }
    } catch (e) {
      console.error("Failed to update progress", e);
      showToast("Unable to update progress.", "error");
    }
  };

  if (loading) return <LoadingState title="Loading course player..." />;
  if (error) return <ErrorState body={error} action={<Button onClick={onExit}>Back to Dashboard</Button>} />;

  return (
    <div className="learner-player" style={{ display: "flex", height: "100vh", background: "var(--surface-bg)", color: "var(--text-primary)", width: "100%", zIndex: 10000, overflow: "hidden" }}>
      {/* Sidebar Navigation — fixed height, internal scroll */}
      <div style={{ flexShrink: 0, width: "300px", height: "100%", overflowY: "auto" }}>
        <CourseSidebar 
          course={courseData} 
          activeModule={activeModule} 
          onSelectModule={setActiveModule}
          progressData={progressData}
          onExit={onExit}
        />
      </div>

      {/* Main Content Area — single scroll region */}
      <div className="player-main" style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", color: "var(--text-primary)" }}>
        {/* Sticky Header */}
        <header style={{ flexShrink: 0, padding: "16px 24px", borderBottom: "1px solid var(--border-subtle)", background: "var(--surface-raised)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ margin: 0, fontSize: "20px", fontWeight: "600" }}>{activeModule?.title || courseData.name}</h2>
          <Button tone="primary" onClick={handleModuleComplete}>Mark Complete</Button>
        </header>

        {/* Scrollable Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "40px", display: "flex", justifyContent: "center" }}>
          <div style={{ maxWidth: "800px", width: "100%" }}>
            {activeModule && activeModule.content?.length > 0 ? (
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
  );
}
