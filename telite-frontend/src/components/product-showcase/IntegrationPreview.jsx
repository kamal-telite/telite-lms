import "./IntegrationPreview.css";

const integrations = [
  { name: "Moodle", status: "Synced", type: "LMS", pulse: true, latency: "12ms", load: 24, tone: "success" },
  { name: "WhatsApp", status: "Active", type: "Comm", pulse: true, latency: "84ms", load: 12, tone: "success" },
  { name: "Zoom", status: "Active", type: "Comm", pulse: false, latency: "42ms", load: 5, tone: "info" },
  { name: "G-Classroom", status: "Active", type: "LMS", pulse: true, latency: "61ms", load: 8, tone: "warning" },
];

const streamLogs = [
  { kind: "sync", time: "[10:45:02]", action: "SYNC:", body: "Moodle -> GradeBook Updated", meta: "(24.2kb)" },
  { kind: "webhook", time: "[10:45:15]", action: "WEBHOOK:", body: "WhatsApp -> Delivery Confirmed", meta: "ID: 9422" },
  { kind: "event", time: "[10:46:01]", action: "EVENT:", body: "Zoom -> Session Sync Initiated", meta: "Latency 42ms" },
];

export default function IntegrationPreview() {
  return (
    <div className="integration-preview">
      <div className="integration-header">
        <div className="mesh-status">Ecosystem Mesh: Operational</div>
        <div className="api-rate">API Throttling: 0.0% | Cache Hit: 94% | Updated 14s ago</div>
      </div>

      <div className="integration-map">
        <div className="center-node">
          <div className="core-label">Telite Hub</div>
          <div className="core-pulse"></div>
        </div>

        <div className="connection-lines">
          {integrations.map((integration, index) => (
            <div
              key={integration.name}
              className={`line ${integration.pulse ? "pulsing" : ""}`}
              style={{ "--angle": `${index * 90}deg` }}
            >
              <div className="line-path"></div>
              <div className={`data-packet tone-${integration.tone}`}></div>
            </div>
          ))}
        </div>

        {integrations.map((integration, index) => (
          <div key={integration.name} className="int-node" style={{ "--angle": `${index * 90}deg` }}>
            <div className={`node-inner ${integration.pulse ? "active" : ""}`}>
               <div className="node-icon">{integration.name[0]}</div>
               <span className="node-name">{integration.name}</span>
               <div className="node-mini-stats">
                  <span>{integration.latency}</span>
                  <div className={`load-dot tone-${integration.tone}`} style={{ opacity: integration.load / 100 + 0.2 }}></div>
               </div>
            </div>
            <span className={`status-badge tone-${integration.tone}`}>{integration.status}</span>
          </div>
        ))}
      </div>

      <div className="event-stream">
        <div className="stream-header">
          <span className="dash-label">Live API Event Stream</span>
          <span className="event-count">14 events/sec</span>
        </div>
        <div className="stream-logs">
          {streamLogs.map((entry) => (
            <div key={`${entry.kind}-${entry.time}`} className={`log-entry ${entry.kind}`}>
              <span className="log-time">{entry.time}</span>
              <span className="log-action">{entry.action}</span>
              {entry.body} <small>{entry.meta}</small>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
