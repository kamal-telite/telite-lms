import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { CourseBuilderLayout } from "./CourseBuilderLayout";
import { LoadingState, ErrorState, useToast } from "../../components/common/ui";
import { getErrorMessage, api } from "../../services/client";

export default function CourseBuilderPage({ session, onLogout }) {
  const { course_id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [course, setCourse] = useState(null);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lockExpiresAt, setLockExpiresAt] = useState(null);
  const heartbeatIntervalRef = useRef(null);

  // 1. Fetch Structure
  const fetchStructure = useCallback(async () => {
    try {
      const { data } = await api.get(`/authoring/courses/${course_id}/builder`);
      setCourse(data.course);
      setSections(data.sections || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load course builder structure."));
    }
  }, [course_id]);

  // 2. Lock Management
  const acquireLock = useCallback(async () => {
    try {
      const { data } = await api.post(`/authoring/courses/${course_id}/lock`);
      setLockExpiresAt(data.expires_at);
      return true;
    } catch (err) {
      setError(getErrorMessage(err, "Failed to acquire lock. Someone else might be editing this course."));
      return false;
    }
  }, [course_id]);

  const releaseLock = useCallback(async () => {
    try {
      await api.delete(`/authoring/courses/${course_id}/lock`);
    } catch (err) {
      console.error("Failed to release lock cleanly", err);
    }
  }, [course_id]);

  const heartbeat = useCallback(async () => {
    try {
      const { data } = await api.post(`/authoring/courses/${course_id}/heartbeat`);
      setLockExpiresAt(data.expires_at);
    } catch (err) {
      console.error("Heartbeat failed", err);
      showToast("Lost connection to course lock. Please refresh to continue editing safely.", "error");
    }
  }, [course_id, showToast]);

  // Lifecycle
  useEffect(() => {
    let active = true;

    async function init() {
      setLoading(true);
      const locked = await acquireLock();
      if (locked && active) {
        await fetchStructure();
        
        // Start heartbeat every 30s
        heartbeatIntervalRef.current = setInterval(() => {
          heartbeat();
        }, 30 * 1000);
      }
      if (active) setLoading(false);
    }
    init();

    return () => {
      active = false;
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
      releaseLock();
    };
  }, [acquireLock, fetchStructure, heartbeat, releaseLock]);

  const handleBack = () => {
    navigate(-1);
  };

  if (loading) {
    return <LoadingState message="Acquiring lock and loading course structure..." />;
  }

  if (error) {
    return (
      <div style={{ padding: "40px", maxWidth: "600px", margin: "0 auto" }}>
        <ErrorState
          title="Cannot open Builder"
          message={error}
          actionLabel="Go Back"
          onAction={handleBack}
        />
      </div>
    );
  }

  return (
    <CourseBuilderLayout
      course={course}
      sections={sections}
      setSections={setSections}
      onBack={handleBack}
      session={session}
      onLogout={onLogout}
    />
  );
}
