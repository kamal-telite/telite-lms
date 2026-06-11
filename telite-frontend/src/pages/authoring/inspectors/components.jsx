import React from "react";

export function TextInput({ label, value, onChange, placeholder = "", type = "text", disabled = false }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "13px", color: "#334155" }}>
      <span>{label}</span>
      <input 
        className="field__input"
        type={type}
        style={{ padding: "6px", fontSize: "13px" }}
        value={value || ""} 
        onChange={(e) => onChange(e.target.value)} 
        placeholder={placeholder} 
        disabled={disabled}
      />
    </label>
  );
}

export function CheckboxInput({ label, checked, onChange, disabled = false }) {
  return (
    <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", fontSize: "13px", color: "#334155" }}>
      <span>{label}</span>
      <input
        type="checkbox"
        checked={Boolean(checked)}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
    </label>
  );
}

export function SelectInput({ label, value, options, onChange, disabled = false }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "13px", color: "#334155" }}>
      <span>{label}</span>
      <select 
        className="field__input" 
        style={{ padding: "6px", fontSize: "13px" }}
        value={value || ""} 
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {options.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
      </select>
    </label>
  );
}
