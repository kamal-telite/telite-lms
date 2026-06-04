import "./LearnerExperience.css";

const courses = [
  { name: "Advanced Cryptography", progress: 85, status: "In Progress", trend: "+5% today", tone: "primary" },
  { name: "System Distributed Design", progress: 100, status: "Completed", trend: "Grade: A+", tone: "success" },
  { name: "Network Infrastructure", progress: 45, status: "In Progress", trend: "Next: Lab 4", tone: "info" },
];

const achievements = [
  { label: "Fast Learner", mark: "FL" },
  { label: "Night Owl", mark: "NO" },
  { label: "More", mark: "+3", muted: true },
];

export default function LearnerExperience() {
  return (
    <div className="learner-experience">
      <div className="learner-header">
        <div className="welcome-msg">
          <span className="dash-label">My Path</span>
          <h3>Keep it up, Alex.</h3>
          <p className="encouragement">You're in the top 5% of your cohort this week.</p>
        </div>
        <div className="stats-pills">
           <div className="stat-pill">
              <span className="pill-label">PAL INDEX</span>
              <span className="pill-val">88.4</span>
           </div>
           <div className="stat-pill">
              <span className="pill-label">STREAK</span>
              <span className="pill-val">12d</span>
           </div>
        </div>
      </div>

      <div className="learner-grid">
        <div className="dash-card modules-card">
          <div className="card-header">
            <span className="dash-label">Active Modules</span>
            <span className="module-count">3 Ongoing</span>
          </div>
          <div className="course-list">
            {courses.map((course) => (
              <div key={course.name} className="course-row">
                <div className="course-info">
                    <span className="course-name">{course.name}</span>
                    <span className="course-trend">{course.trend}</span>
                </div>
                <div className="progress-container">
                  <div className="progress-bar">
                    <div className={`progress-fill tone-${course.tone}`} style={{ width: `${course.progress}%` }}></div>
                  </div>
                  <span className="progress-val">{course.progress}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="sidebar-column">
          <div className="dash-card ai-coach">
            <div className="card-header">
               <span className="dash-label">AI Learning Coach</span>
               <div className="ai-pulse"></div>
            </div>
            <div className="rec-list">
              <div className="rec-item">
                <div className="rec-icon">AI</div>
                <p><strong>Optimize:</strong> Your symmetric cipher retention is dipping. Quick 5m review?</p>
              </div>
              <div className="rec-item">
                <div className="rec-icon">GO</div>
                <p><strong>Ready:</strong> You've unlocked the <em>Advanced Routing</em> lab early.</p>
              </div>
            </div>
          </div>

          <div className="dash-card achievements">
             <span className="dash-label">Recent Achievements</span>
             <div className="badge-row">
                {achievements.map((badge) => (
                  <div
                    key={badge.label}
                    className={`badge-item ${badge.muted ? "empty" : ""}`}
                    title={badge.label}
                  >
                    {badge.mark}
                  </div>
                ))}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
