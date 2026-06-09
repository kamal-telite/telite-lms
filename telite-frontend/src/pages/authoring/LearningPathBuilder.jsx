import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { DndContext, closestCenter, useSensor, useSensors, PointerSensor, KeyboardSensor } from "@dnd-kit/core";
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button, IconButton, Badge, LoadingState, ErrorState, useToast, Modal } from "../../components/common/ui";
import { api, getErrorMessage } from "../../services/client";

function SortableCourseItem({ course, index, onRemove, onSettings }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: course.id });
  
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    marginBottom: "12px",
    display: "flex",
    alignItems: "center",
    gap: "16px",
    boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
  };

  return (
    <div ref={setNodeRef} style={style}>
      <div {...attributes} {...listeners} style={{ cursor: "grab", color: "#94a3b8" }}>
        ☰
      </div>
      <div style={{ fontWeight: 600, width: "30px", color: "#64748b" }}>{index + 1}.</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 500, color: "#0f172a" }}>{course.name}</div>
        <div style={{ fontSize: "12px", color: "#64748b" }}>{course.category_slug || 'Uncategorized'}</div>
      </div>
      {course.settings?.require_previous && (
        <Badge tone="warning">Requires Previous</Badge>
      )}
      <Button tone="neutral" size="small" onClick={() => onSettings(course)}>Rules</Button>
      <IconButton icon="trash" size="small" onClick={() => onRemove(course.id)} />
    </div>
  );
}

export function LearningPathBuilder() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [pathData, setPathData] = useState(null);
  const [courses, setCourses] = useState([]);
  const [allCourses, setAllCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [analytics, setAnalytics] = useState(null);

  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [activeCourse, setActiveCourse] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const fetchData = useCallback(async () => {
    try {
      const [pathRes, coursesRes, analyticsRes] = await Promise.all([
        api.get(`/authoring/learning-paths/${pathId}`),
        api.get(`/platform/courses`), // assume this gets all org courses
        api.get(`/authoring/learning-paths/${pathId}/analytics`).catch(() => ({ data: null }))
      ]);
      
      setPathData(pathRes.data.path);
      
      // Match path courses with rich course details
      const pathCourseIds = pathRes.data.path.courses.map(c => c.course_id);
      const detailedCourses = pathCourseIds.map(id => {
        const fullCourse = coursesRes.data.courses.find(c => c.id === id) || { id, name: "Unknown Course" };
        const settings = pathRes.data.path.settings?.course_rules?.[id] || {};
        return { ...fullCourse, settings };
      });
      
      setCourses(detailedCourses);
      setAllCourses(coursesRes.data.courses);
      
      if (analyticsRes?.data?.analytics) {
        setAnalytics(analyticsRes.data.analytics);
      }
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to load path."), "error");
    } finally {
      setLoading(false);
    }
  }, [pathId, showToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      setCourses((items) => {
        const oldIndex = items.findIndex(i => i.id === active.id);
        const newIndex = items.findIndex(i => i.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Save sequence
      await api.post(`/authoring/learning-paths/${pathId}/sequence`, {
        course_ids: courses.map(c => c.id)
      });
      
      // Save settings
      const newSettings = { ...pathData.settings, course_rules: {} };
      courses.forEach(c => {
        if (c.settings) newSettings.course_rules[c.id] = c.settings;
      });
      
      await api.put(`/authoring/learning-paths/${pathId}`, {
        title: pathData.title,
        description: pathData.description,
        settings: newSettings
      });
      
      showToast("Learning path saved successfully.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to save path."), "error");
    } finally {
      setSaving(false);
    }
  };

  const addCourse = (courseId) => {
    if (courses.find(c => c.id === courseId)) return;
    const course = allCourses.find(c => c.id === courseId);
    if (course) setCourses([...courses, { ...course, settings: {} }]);
  };

  const removeCourse = (courseId) => {
    setCourses(courses.filter(c => c.id !== courseId));
  };

  const openSettings = (course) => {
    setActiveCourse(course);
    setSettingsModalOpen(true);
  };

  const saveCourseSettings = (settings) => {
    setCourses(courses.map(c => c.id === activeCourse.id ? { ...c, settings } : c));
    setSettingsModalOpen(false);
  };

  if (loading) return <LoadingState message="Loading Path Builder..." />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8fafc' }}>
      <header style={{ padding: '16px 24px', background: '#fff', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ margin: '0 0 4px 0', fontSize: '20px' }}>{pathData?.title}</h2>
          <div style={{ color: '#64748b', fontSize: '14px' }}>Learning Path Orchestrator</div>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <Button tone="neutral" onClick={() => navigate('/admin')}>Exit</Button>
          <Button tone="primary" disabled={saving} onClick={handleSave}>Save Path</Button>
        </div>
      </header>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Main Canvas */}
        <div style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
          <h3 style={{ marginBottom: '24px' }}>Course Sequence</h3>
          
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={courses.map(c => c.id)} strategy={verticalListSortingStrategy}>
              {courses.map((course, idx) => (
                <SortableCourseItem 
                  key={course.id} 
                  index={idx} 
                  course={course} 
                  onRemove={removeCourse}
                  onSettings={openSettings}
                />
              ))}
            </SortableContext>
          </DndContext>

          <div style={{ marginTop: '24px', padding: '24px', background: '#fff', border: '1px dashed #cbd5e1', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ marginBottom: '12px', color: '#64748b' }}>Add Course to Path</div>
            <select className="field__input" style={{ maxWidth: '300px', margin: '0 auto' }} onChange={(e) => { if(e.target.value) addCourse(e.target.value); e.target.value=''; }}>
              <option value="">-- Select Course --</option>
              {allCourses.filter(c => !courses.find(pc => pc.id === c.id)).map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Analytics Pane */}
        <div style={{ width: '350px', background: '#fff', borderLeft: '1px solid #e2e8f0', padding: '24px', overflowY: 'auto' }}>
          <h3 style={{ marginBottom: '24px' }}>Path Analytics</h3>
          {analytics ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ padding: '16px', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                <div style={{ fontSize: '13px', color: '#166534', fontWeight: 600 }}>Path Completion Rate</div>
                <div style={{ fontSize: '32px', fontWeight: 700, color: '#15803d' }}>{analytics.path_completion_percentage}%</div>
              </div>
              
              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ flex: 1, padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>Enrolled</div>
                  <div style={{ fontSize: '20px', fontWeight: 600 }}>{analytics.total_enrolled}</div>
                </div>
                <div style={{ flex: 1, padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>Completed</div>
                  <div style={{ fontSize: '20px', fontWeight: 600 }}>{analytics.completed_learners}</div>
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>Course Bottlenecks</h4>
                {analytics.courses_stats.map(stat => {
                  const courseName = allCourses.find(c => c.id === stat.course_id)?.name || stat.course_id;
                  return (
                    <div key={stat.course_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                      <div style={{ fontSize: '13px', color: stat.is_bottleneck ? '#ef4444' : '#334155' }}>
                        {stat.is_bottleneck && '⚠️ '} {courseName}
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>{stat.completion_rate}%</div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div style={{ color: '#64748b', fontSize: '14px' }}>Analytics not available for this path yet.</div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      {settingsModalOpen && activeCourse && (
        <Modal open={true} onClose={() => setSettingsModalOpen(false)} title={`Rules: ${activeCourse.name}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input 
                type="checkbox" 
                id="require_prev" 
                defaultChecked={activeCourse.settings?.require_previous} 
                onChange={(e) => activeCourse.settings.require_previous = e.target.checked}
              />
              <label htmlFor="require_prev">Require previous course to be completed</label>
            </div>
            
            <div>
              <label className="field__label">Minimum Quiz Pass Requirement (%)</label>
              <input 
                className="field__input" 
                type="number" 
                defaultValue={activeCourse.settings?.min_score || 0}
                onChange={(e) => activeCourse.settings.min_score = parseInt(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input 
                type="checkbox" 
                id="req_cert" 
                defaultChecked={activeCourse.settings?.require_certificate} 
                onChange={(e) => activeCourse.settings.require_certificate = e.target.checked}
              />
              <label htmlFor="req_cert">Require Certificate issuance to unlock next</label>
            </div>

            <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
              <Button tone="primary" onClick={() => saveCourseSettings(activeCourse.settings)}>Save Rules</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
