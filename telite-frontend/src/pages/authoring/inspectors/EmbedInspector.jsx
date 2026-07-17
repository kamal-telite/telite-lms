import React, { useState } from "react";
import { TextInput } from "./components";
import { validateEmbedUrl } from "../../../utils/embedUtils";

export default function EmbedInspector({ settings, onChange, disabled }) {
  const [urlError, setUrlError] = useState("");

  const handleUrlChange = (value) => {
    onChange("url", value);
    
    if (value && value.trim()) {
      const validation = validateEmbedUrl(value);
      setUrlError(validation.error || "");
    } else {
      setUrlError("");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <TextInput 
        label="URL" 
        value={settings.url} 
        placeholder="https://www.youtube.com/watch?v=..." 
        onChange={handleUrlChange} 
        disabled={disabled} 
      />
      {urlError && (
        <div style={{ color: "var(--error)", fontSize: "13px", marginTop: "-8px" }}>
          {urlError}
        </div>
      )}
      <TextInput 
        label="Sandbox Policy" 
        value={settings.sandbox_policy} 
        placeholder="allow-scripts allow-same-origin" 
        onChange={(v) => onChange("sandbox_policy", v)} 
        disabled={disabled} 
      />
    </div>
  );
}
