import React from "react";
import { SelectInput } from "./components";

export default function ScormInspector({ settings, onChange, disabled }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <SelectInput 
        label="Launch Mode" 
        value={settings.launch_mode || "inline"} 
        onChange={(v) => onChange("launch_mode", v)} 
        options={[{label: "Inline", value: "inline"}, {label: "New Window", value: "popup"}]}
        disabled={disabled}
      />
    </div>
  );
}
