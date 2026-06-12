export default function RouteChunkFallback() {
  return (
    <div
      className="loader"
      style={{ display: "flex", flexDirection: "column", zIndex: 999999 }}
      aria-busy="true"
      aria-label="Loading page"
    >
      <div className="loader-logo">
        Telite <span>LMS</span>
      </div>
      <div
        style={{
          marginTop: "24px",
          fontSize: "13px",
          color: "rgba(255,255,255,0.5)",
          letterSpacing: "0.05em",
        }}
      >
        Loading workspace…
      </div>
    </div>
  );
}
