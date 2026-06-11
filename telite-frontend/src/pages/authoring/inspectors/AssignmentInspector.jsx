import React from "react";
import { TextInput, SelectInput } from "./components";

export default function AssignmentInspector({ settings, onChange, disabled }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <SelectInput 
        label="Submission Mode" 
        value={settings.submission_mode || "both"} 
        onChange={(v) => onChange("submission_mode", v)} 
        options={[{label: "File & Text", value: "both"}, {label: "File Upload Only", value: "file"}, {label: "Text Entry Only", value: "text"}]}
        disabled={disabled}
      />
      <TextInput label="Due Date" type="date" value={settings.due_date} onChange={(v) => onChange("due_date", v)} disabled={disabled} />
      <TextInput label="Points" type="number" value={settings.points} onChange={(v) => onChange("points", v)} disabled={disabled} />
    </div>
  );
}
