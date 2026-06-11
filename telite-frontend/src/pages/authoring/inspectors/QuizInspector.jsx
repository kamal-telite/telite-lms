import React from "react";
import { TextInput, CheckboxInput } from "./components";

export default function QuizInspector({ settings, onChange, disabled }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <TextInput label="Passing Score (%)" type="number" value={settings.passing_score} onChange={(v) => onChange("passing_score", v)} disabled={disabled} />
      <TextInput label="Attempts (0 = infinite)" type="number" value={settings.attempts} onChange={(v) => onChange("attempts", v)} disabled={disabled} />
      <TextInput label="Timer (minutes)" type="number" value={settings.timer_minutes} onChange={(v) => onChange("timer_minutes", v)} disabled={disabled} />
      <CheckboxInput label="Shuffle Questions" checked={settings.shuffle} onChange={(v) => onChange("shuffle", v)} disabled={disabled} />
    </div>
  );
}
