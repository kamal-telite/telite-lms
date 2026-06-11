import React from "react";
import { TextInput, CheckboxInput } from "./components";

export default function AudioInspector({ settings, onChange, disabled }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <TextInput label="Transcript URL" value={settings.transcript_url} onChange={(v) => onChange("transcript_url", v)} disabled={disabled} />
      <CheckboxInput label="Allow Download" checked={settings.allow_download} onChange={(v) => onChange("allow_download", v)} disabled={disabled} />
      <CheckboxInput label="Autoplay" checked={settings.autoplay} onChange={(v) => onChange("autoplay", v)} disabled={disabled} />
    </div>
  );
}
