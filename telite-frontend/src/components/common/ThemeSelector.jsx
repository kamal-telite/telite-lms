import { useTheme } from "../../providers/ThemeProvider";

const THEME_OPTIONS = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

export default function ThemeSelector({ compact = false }) {
  const { mode, resolvedTheme, setTheme } = useTheme();

  if (compact) {
    return (
      <div className="theme-selector" role="radiogroup" aria-label="Appearance">
        {THEME_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`theme-selector__option ${mode === option.value ? "is-active" : ""}`}
            onClick={() => setTheme(option.value)}
            role="radio"
            aria-checked={mode === option.value}
          >
            <span>{option.label}</span>
            {mode === option.value ? <span aria-hidden="true">On</span> : null}
          </button>
        ))}
      </div>
    );
  }

  return (
    <label className="theme-selector-field">
      <span>Appearance</span>
      <select
        value={mode}
        onChange={(event) => setTheme(event.target.value)}
        aria-label={`Appearance, currently ${mode}. Resolved theme ${resolvedTheme}.`}
      >
        {THEME_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
