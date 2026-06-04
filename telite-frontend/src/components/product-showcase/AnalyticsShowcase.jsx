import "./AnalyticsShowcase.css";

const riskVectors = [
  { label: "Critical Intervention", value: 12, tone: "danger" },
  { label: "Performance Dip", value: 45, tone: "warning" },
  { label: "At-Risk Engagement", value: 89, tone: "info" },
];

const learnerStream = [
  { initials: "JS", name: "John S.", action: "completed Module 4", meta: "2m ago | Score: 98%" },
  { initials: "MA", name: "Maria A.", action: "started Live Lab", meta: "5m ago | Latency: 24ms" },
];

export default function AnalyticsShowcase() {
  return (
    <div className="analytics-showcase">
      <div className="analytics-header">
        <div className="sync-status">
          <span className="pulse-dot"></span>
          Live Ops: All Systems Synchronized
        </div>
        <div className="timestamp">Last Compute: {new Date().toLocaleTimeString()}</div>
      </div>

      <div className="analytics-grid">
        <div className="analytics-card main-metric">
          <div className="metric-header">
            <span className="metric-label">System-Wide PAL Score</span>
            <span className="info-icon" aria-hidden="true">i</span>
          </div>
          <div className="metric-value">
            92.4 <small className="metric-unit">/ 100</small>
          </div>
          <div className="metric-trend positive">
            <span className="trend-arrow" aria-hidden="true">+</span> 4.2% <small>vs last 30d</small>
          </div>
          <div className="micro-data">Confidence: 98.2% | Variance: +/- 0.4</div>
        </div>

        <div className="analytics-card risk-prediction">
          <span className="metric-label">Learner Risk Vectors</span>
          <div className="risk-container">
            {riskVectors.map((item) => (
              <div key={item.label} className="risk-item">
                <div className="risk-info">
                  <span className="risk-name">{item.label}</span>
                  <span className={`risk-count tone-${item.tone}`}>{item.value}</span>
                </div>
                <div className="risk-bar">
                  <div
                    className={`risk-fill tone-${item.tone}`}
                    style={{ width: `${item.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="analytics-card ai-insight">
          <div className="insight-header">
            <span className="insight-badge">Prediction: 94% Confidence</span>
            <span className="insight-time">Real-time</span>
          </div>
          <p className="insight-text">
            <strong>Advanced Cryptography</strong>: 214 learners projected to fail module assessment within 48h based on current engagement velocity.
          </p>
          <div className="insight-actions">
            <button className="insight-btn primary">Distribute Remedial Path</button>
            <button className="insight-btn secondary">Simulate Impact</button>
          </div>
        </div>

        <div className="analytics-card heatmap-preview">
          <div className="metric-header">
            <span className="metric-label">Cognitive Engagement Map</span>
            <div className="legend">
              <span className="low"></span>
              <span className="med"></span>
              <span className="high"></span>
            </div>
          </div>
          <div className="heatmap-grid">
            {[...Array(35)].map((_, index) => (
              <div
                key={index}
                className={`heat-cell ${index % 7 === 0 ? "high" : index % 5 === 0 ? "med" : "low"}`}
                title={`Node ${index}: ${80 + (index % 20)}% engagement`}
              />
            ))}
          </div>
        </div>

        <div className="analytics-card activity-feed">
          <span className="metric-label">Active Learner Stream</span>
          <div className="feed-list">
            {learnerStream.map((item) => (
              <div key={item.name} className="feed-item">
                <div className="feed-avatar">{item.initials}</div>
                <div className="feed-content">
                  <strong>{item.name}</strong> {item.action}
                  <span>{item.meta}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
