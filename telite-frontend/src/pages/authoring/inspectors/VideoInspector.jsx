import React from "react";
import { TextInput, SelectInput, CheckboxInput } from "./components";

export default function VideoInspector({ settings, onChange, disabled }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <TextInput label="Poster Image URL" value={settings.poster_image} onChange={(v) => onChange("poster_image", v)} disabled={disabled} />
      <TextInput label="Transcript URL" value={settings.transcript_url} onChange={(v) => onChange("transcript_url", v)} disabled={disabled} />
      <SelectInput 
        label="Playback Speed" 
        value={settings.playback_speed || "1.0"} 
        onChange={(v) => onChange("playback_speed", v)} 
        options={[{label: "0.5x", value: "0.5"}, {label: "1.0x", value: "1.0"}, {label: "1.25x", value: "1.25"}, {label: "1.5x", value: "1.5"}, {label: "2.0x", value: "2.0"}]}
        disabled={disabled}
      />
      <CheckboxInput label="Autoplay" checked={settings.autoplay} onChange={(v) => onChange("autoplay", v)} disabled={disabled} />
    </div>
  );
}
