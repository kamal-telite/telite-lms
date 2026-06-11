import React from "react";
import { CheckboxInput } from "./components";

export default function PdfInspector({ settings, onChange, disabled }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <CheckboxInput label="Allow Download" checked={settings.allow_download} onChange={(v) => onChange("allow_download", v)} disabled={disabled} />
      <CheckboxInput label="Open in New Tab" checked={settings.open_new_tab} onChange={(v) => onChange("open_new_tab", v)} disabled={disabled} />
      <CheckboxInput label="Show Toolbar" checked={settings.show_toolbar} onChange={(v) => onChange("show_toolbar", v)} disabled={disabled} />
    </div>
  );
}
