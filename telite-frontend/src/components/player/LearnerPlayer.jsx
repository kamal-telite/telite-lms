import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, LoadingState, ErrorState, Icon } from "../common/ui";
import { CourseSidebar } from "./CourseSidebar";
import { BlockRenderer } from "./BlockRenderer";

export function LearnerPlayer({ courseId, onExit }) {
  const [courseData, setCourseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeModule, setActiveModule] = useState(null);
  const [progressData, setProgressData] = useState({});

  useEffect(() => {
    async function loadCourse() {
      try {
        const token = localStorage.getItem("token");
        // Get course details
        const res = await fetch(`/api/v1/learner/courses/${courseId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Failed to load course details");
        const data = await res.json();
        setCourseData(data);
        
        // Get resume state
        const resumeRes = await fetch(`/api/v1/learner/resume/${courseId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (resumeRes.ok) {
          const resumeData = await resumeRes.json();
          // Find the module to activate
          if (resumeData.last_module_id && data.modules_json) {
            const mod = data.modules_json.find(m => m.id === resumeData.last_module_id);
            if (mod) setActiveModule(mod);
            else if (data.modules_json.length > 0) setActiveModule(data.modules_json[0]);
          } else if (data.modules_json && data.modules_json.length > 0) {
            setActiveModule(data.modules_json[0]);
          }
        } else if (data.modules_json && data.modules_json.length > 0) {
           setActiveModule(data.modules_json[0]);
        }
      } catch (err) {
        setError(err.message);
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
      const token = localStorage.getItem("token");
      fetch("/api/v1/learner/heartbeat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          course_id: courseId,
          module_id: activeModule?.id || null,
          time_spent_seconds: 15
        })
      }).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, [courseId, activeModule]);

  useEffect(() => {
    // Emit MODULE_STARTED
    if (activeModule && courseId) {
      const token = localStorage.getItem("token");
      // Prevent duplicate starts if already completed or tracked recently? 
      // The backend can handle deduplication or we just blindly send it.
      fetch("/api/v1/learner/events", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          events: [{
            event_type: "MODULE_STARTED",
            course_id: courseId,
            module_id: activeModule.id
          }]
        })
      }).catch(() => {});
    }
  }, [activeModule?.id, courseId]);

  const handleModuleComplete = async () => {
    if (!activeModule) return;
    const token = localStorage.getItem("token");
    try {
      await fetch("/api/v1/learner/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          course_id: courseId,
          module_updates: [{ module_id: activeModule.id, status: "completed" }]
        })
      });
      // Update local progress state
      setProgressData(prev => ({ ...prev, [activeModule.id]: "completed" }));
      
      // Auto-advance to next module
      const currentIndex = courseData.modules_json.findIndex(m => m.id === activeModule.id);
      if (currentIndex >= 0 && currentIndex < courseData.modules_json.length - 1) {
        setActiveModule(courseData.modules_json[currentIndex + 1]);
      }
    } catch (e) {
      console.error("Failed to update progress", e);
    }
  };

  if (loading) return <LoadingState title="Loading course player..." />;
  if (error) return <ErrorState body={error} action={<Button onClick={onExit}>Back to Dashboard</Button>} />;

  return (
    <div className="learner-player" style={{ display: "flex", height: "100vh", width: "100vw", background: "var(--background)", position: "fixed", top: 0, left: 0, zIndex: 10000 }}>
      {/* Sidebar Navigation */}
      <CourseSidebar 
        course={courseData} 
        activeModule={activeModule} 
        onSelectModule={setActiveModule}
        progressData={progressData}
        onExit={onExit}
      />

      {/* Main Content Area */}
      <div className="player-main" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Header */}
        <header style={{ padding: "16px 24px", borderBottom: "1px solid var(--border)", background: "var(--surface)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ margin: 0, fontSize: "20px", fontWeight: "600" }}>{activeModule?.title || courseData.name}</h2>
          <Button tone="primary" onClick={handleModuleComplete}>Mark Complete</Button>
        </header>

        {/* Content Scroll Area */}
        <div style={{ flex: 1, overflowY: "auto", padding: "40px", display: "flex", justifyContent: "center" }}>
          <div style={{ maxWidth: "800px", width: "100%" }}>
            {activeModule ? (
              <BlockRenderer content={activeModule.content} courseId={courseId} moduleId={activeModule.id} />
            ) : (
              <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                Select a module to begin
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
