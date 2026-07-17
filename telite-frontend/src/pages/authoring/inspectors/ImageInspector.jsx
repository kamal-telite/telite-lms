import React from "react";
import { TextInput, SelectInput, CheckboxInput } from "./components";

export default function ImageInspector({ settings, onChange, disabled }) {
  const alignment = settings.alignment || "left";
  const sizePreset = settings.size_preset || "custom";
  const position = settings.position || "inline";
  const maintainAspectRatio = settings.maintain_aspect_ratio !== false;

  const handleSizePresetChange = (value) => {
    onChange("size_preset", value);
    // Auto-set width/height based on preset
    switch (value) {
      case "small":
        onChange("width", "200px");
        onChange("height", "");
        break;
      case "medium":
        onChange("width", "400px");
        onChange("height", "");
        break;
      case "large":
        onChange("width", "600px");
        onChange("height", "");
        break;
      case "full":
        onChange("width", "100%");
        onChange("height", "");
        break;
      case "custom":
        // Don't change existing values
        break;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Basic Properties */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", paddingBottom: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <TextInput label="Alt Text" value={settings.alt_text} onChange={(v) => onChange("alt_text", v)} disabled={disabled} placeholder="Describe the image for accessibility" />
        <TextInput label="Caption" value={settings.caption} onChange={(v) => onChange("caption", v)} disabled={disabled} placeholder="Optional caption below the image" />
      </div>

      {/* Size & Position */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", paddingBottom: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text-primary)" }}>Size & Position</div>
        
        <SelectInput 
          label="Size Preset" 
          value={sizePreset} 
          onChange={handleSizePresetChange} 
          options={[
            {label: "Small (200px)", value: "small"},
            {label: "Medium (400px)", value: "medium"},
            {label: "Large (600px)", value: "large"},
            {label: "Full Width", value: "full"},
            {label: "Custom", value: "custom"}
          ]}
          disabled={disabled}
        />

        <div style={{ display: "flex", gap: "8px" }}>
          <TextInput label="Width" value={settings.width || ""} onChange={(v) => onChange("width", v)} disabled={disabled} placeholder="e.g., 400px or 50%" />
          <TextInput label="Height" value={settings.height || ""} onChange={(v) => onChange("height", v)} disabled={disabled} placeholder="e.g., 300px or auto" />
        </div>

        <CheckboxInput 
          label="Maintain aspect ratio" 
          checked={maintainAspectRatio} 
          onChange={(v) => onChange("maintain_aspect_ratio", v)} 
          disabled={disabled}
        />

        <SelectInput 
          label="Position" 
          value={position} 
          onChange={(v) => onChange("position", v)} 
          options={[
            {label: "Inline with text", value: "inline"},
            {label: "Above text", value: "above"},
            {label: "Below text", value: "below"},
            {label: "Between paragraphs", value: "between"}
          ]}
          disabled={disabled}
        />

        <SelectInput 
          label="Alignment" 
          value={alignment} 
          onChange={(v) => onChange("alignment", v)} 
          options={[
            {label: "Left", value: "left"},
            {label: "Center", value: "center"},
            {label: "Right", value: "right"}
          ]}
          disabled={disabled}
        />
      </div>

      {/* Spacing */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", paddingBottom: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text-primary)" }}>Spacing (px)</div>
        
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <TextInput label="Top Margin" value={settings.margin_top || ""} onChange={(v) => onChange("margin_top", v)} disabled={disabled} placeholder="0" />
          <TextInput label="Bottom Margin" value={settings.margin_bottom || ""} onChange={(v) => onChange("margin_bottom", v)} disabled={disabled} placeholder="0" />
          <TextInput label="Left Margin" value={settings.margin_left || ""} onChange={(v) => onChange("margin_left", v)} disabled={disabled} placeholder="0" />
          <TextInput label="Right Margin" value={settings.margin_right || ""} onChange={(v) => onChange("margin_right", v)} disabled={disabled} placeholder="0" />
        </div>
      </div>

      {/* Styling */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text-primary)" }}>Styling</div>
        
        <SelectInput 
          label="Border Style" 
          value={settings.border_style || "none"} 
          onChange={(v) => onChange("border_style", v)} 
          options={[
            {label: "No Border", value: "none"},
            {label: "Solid", value: "solid"},
            {label: "Dashed", value: "dashed"},
            {label: "Dotted", value: "dotted"},
            {label: "Double", value: "double"}
          ]}
          disabled={disabled}
        />

        {settings.border_style && settings.border_style !== "none" && (
          <div style={{ display: "flex", gap: "8px" }}>
            <TextInput label="Border Width" value={settings.border_width || ""} onChange={(v) => onChange("border_width", v)} disabled={disabled} placeholder="e.g., 2px" />
            <TextInput label="Border Color" value={settings.border_color || ""} onChange={(v) => onChange("border_color", v)} disabled={disabled} placeholder="#000000" />
          </div>
        )}

        <TextInput label="Border Radius" value={settings.border_radius || ""} onChange={(v) => onChange("border_radius", v)} disabled={disabled} placeholder="e.g., 8px or 50%" />

        <SelectInput 
          label="Shadow" 
          value={settings.shadow || "none"} 
          onChange={(v) => onChange("shadow", v)} 
          options={[
            {label: "No Shadow", value: "none"},
            {label: "Small", value: "small"},
            {label: "Medium", value: "medium"},
            {label: "Large", value: "large"}
          ]}
          disabled={disabled}
        />

        <CheckboxInput 
          label="Responsive (adjust for mobile)" 
          checked={settings.responsive !== false} 
          onChange={(v) => onChange("responsive", v)} 
          disabled={disabled}
        />
      </div>
    </div>
  );
}
