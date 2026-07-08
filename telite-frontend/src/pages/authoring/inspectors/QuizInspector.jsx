import React from "react";
import { TextInput, CheckboxInput } from "./components";

export default function QuizInspector({ settings, onChange, disabled }) {
  const maxAttempts = Number(settings.max_attempts || 0);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <TextInput label="Passing Score (%)" type="number" value={settings.passing_score} onChange={(v) => onChange("passing_score", Number(v))} disabled={disabled} />
      <label className="field">
        <span className="field__label">Maximum Attempts</span>
        <select className="field__input" value={maxAttempts === 0 ? "unlimited" : String(maxAttempts)} onChange={(event) => onChange("max_attempts", event.target.value === "unlimited" ? 0 : Number(event.target.value))} disabled={disabled}>
          <option value="unlimited">Unlimited</option>
          {[1, 2, 3, 5].map((value) => <option key={value} value={value}>{value}</option>)}
          {maxAttempts > 0 && ![1, 2, 3, 5].includes(maxAttempts) ? <option value={maxAttempts}>{maxAttempts}</option> : null}
        </select>
      </label>
      <TextInput label="Timer (minutes)" type="number" value={settings.timer_minutes} onChange={(v) => onChange("timer_minutes", Number(v))} disabled={disabled} />
      <CheckboxInput label="Shuffle Questions" checked={settings.shuffle} onChange={(v) => onChange("shuffle", v)} disabled={disabled} />
    </div>
  );
}
