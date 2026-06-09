import { useEffect, useState, useRef } from "react";
import { offlineSyncManager } from "../../lib/offlineSyncManager";
import { Button, LoadingState, ErrorState } from "../common/ui";

export function NativePlayer({ cmid, onExit }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [launchData, setLaunchData] = useState(null);
  const iframeRef = useRef(null);

  useEffect(() => {
    async function initPlayer() {
      try {
        const token = localStorage.getItem("token");
        const res = await fetch(`/api/player/modules/${cmid}/launch`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (!res.ok) throw new Error("Failed to load module");
        const data = await res.json();
        setLaunchData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    initPlayer();
  }, [cmid]);

  useEffect(() => {
    // Setup SCORM API adapter on window object
    if (!launchData) return;

    // This is a minimal SCORM 1.2 API adapter mock
    // In a full implementation, we'd handle Initialize, Terminate, GetValue, SetValue
    const trackingQueue = [];
    
    window.API = {
      LMSInitialize: () => "true",
      LMSFinish: () => {
        flushTracking();
        return "true";
      },
      LMSGetValue: (element) => {
        return launchData.resume_state?.[element] || "";
      },
      LMSSetValue: (element, value) => {
        trackingQueue.push({ element, value });
        return "true";
      },
      LMSCommit: () => {
        flushTracking();
        return "true";
      },
      LMSGetLastError: () => "0",
      LMSGetErrorString: () => "No error",
      LMSGetDiagnostic: () => "No error"
    };

    async function flushTracking() {
      if (trackingQueue.length === 0) return;
      
      const events = [...trackingQueue];
      trackingQueue.length = 0; // clear queue
      
      // Determine protocol from launch data or default to scorm_12
      const protocol = "scorm_12"; 
      
      // Check for completion/score
      const statusEvent = events.find(e => e.element === "cmi.core.lesson_status");
      const scoreEvent = events.find(e => e.element === "cmi.core.score.raw");
      
      const status = statusEvent ? statusEvent.value : null;
      const score = scoreEvent ? parseFloat(scoreEvent.value) : null;

      await offlineSyncManager.queueTrackingEvent(
        cmid,
        protocol,
        events,
        status,
        score,
        0 // time_spent_seconds handled by backend if needed, or calculated here
      );
    }

    // Auto-flush on interval (autosave)
    const interval = setInterval(flushTracking, 10000);

    return () => {
      flushTracking(); // flush on unmount
      clearInterval(interval);
      delete window.API;
    };
  }, [launchData, cmid]);

  if (loading) return <LoadingState title="Loading module..." />;
  if (error) return <ErrorState body={error} action={<Button onClick={onExit}>Back to Course</Button>} />;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", background: "#fff" }}>
      <div style={{ padding: "12px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--surface)" }}>
        <h2 style={{ margin: 0, fontSize: "16px" }}>Interactive Module</h2>
        <Button size="small" tone="ghost" onClick={onExit}>Exit Activity</Button>
      </div>
      
      <div style={{ flex: 1, position: "relative" }}>
        {launchData.module_type === "h5pactivity" ? (
           // Native H5P renderer integration would go here.
           // For now, load the standalone HTML.
           <iframe
             ref={iframeRef}
             src={launchData.launch_url}
             title="H5P Interactive Content"
             style={{ width: "100%", height: "100%", border: "none" }}
           />
        ) : (
           <iframe
             ref={iframeRef}
             src={launchData.launch_url}
             title="SCORM Interactive Content"
             style={{ width: "100%", height: "100%", border: "none" }}
           />
        )}
      </div>
    </div>
  );
}
