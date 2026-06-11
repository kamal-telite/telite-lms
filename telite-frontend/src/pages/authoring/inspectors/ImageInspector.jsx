import React from "react";
import { TextInput, SelectInput } from "./components";

export default function ImageInspector({ settings, onChange, disabled }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <TextInput label="Alt Text" value={settings.alt_text} onChange={(v) => onChange("alt_text", v)} disabled={disabled} />
      <TextInput label="Caption" value={settings.caption} onChange={(v) => onChange("caption", v)} disabled={disabled} />
      <SelectInput 
        label="Alignment" 
        value={settings.alignment || "left"} 
        onChange={(v) => onChange("alignment", v)} 
        options={[{label: "Left", value: "left"}, {label: "Center", value: "center"}, {label: "Right", value: "right"}]}
        disabled={disabled}
      />
      <div style={{ display: "flex", gap: "8px" }}>
        <TextInput label="Width" value={settings.width} onChange={(v) => onChange("width", v)} disabled={disabled} />
        <TextInput label="Height" value={settings.height} onChange={(v) => onChange("height", v)} disabled={disabled} />
      </div>
    </div>
  );
}
