import React from "react";
import { TextInput } from "./components";

export default function EmbedInspector({ settings, onChange, disabled }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <TextInput label="URL" value={settings.url} placeholder="https://..." onChange={(v) => onChange("url", v)} disabled={disabled} />
      <TextInput label="Sandbox Policy" value={settings.sandbox_policy} placeholder="allow-scripts allow-same-origin" onChange={(v) => onChange("sandbox_policy", v)} disabled={disabled} />
    </div>
  );
}
