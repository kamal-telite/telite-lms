import React, { useEffect, useRef, useState } from "react";
import { useFocusTrap } from "../../../hooks/useFocusTrap";
import "../../../styles/landing-sections/palette.css";

const COMMANDS = [
  { id: "pricing", label: "Go to Pricing", icon: "$", shortcut: "P", action: () => document.getElementById("pricing")?.scrollIntoView({ behavior: "smooth" }) },
  { id: "demo", label: "Open Demo", icon: "+", shortcut: "D", action: (ctx) => ctx.setShowContactModal(true) },
  { id: "docs", label: "View Documentation", icon: "[]", shortcut: "G", action: () => window.open("#", "_blank") },
  { id: "integrations", label: "Explore Integrations", icon: "@", shortcut: "I", action: () => document.getElementById("integrations")?.scrollIntoView({ behavior: "smooth" }) },
  { id: "security", label: "Security & Compliance", icon: "!", shortcut: "S", action: () => document.getElementById("security-trust")?.scrollIntoView({ behavior: "smooth" }) },
  { id: "theme", label: "Toggle Theme", icon: "~", shortcut: "T", action: (ctx) => ctx.toggleTheme() },
  { id: "status", label: "System Status: Operational", icon: "*", shortcut: "O", action: () => {} },
];

export default function CommandPalette({ isOpen, onClose, context }) {
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [announcement, setAnnouncement] = useState("");
  const inputRef = useRef(null);
  const modalRef = useRef(null);

  useFocusTrap(isOpen, modalRef);

  const filteredCommands = COMMANDS.filter((cmd) =>
    cmd.label.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setSelectedIndex(0);
      setSearch("");
      setAnnouncement("Command palette opened. 7 commands available.");
    }
  }, [isOpen]);

  useEffect(() => {
    if (filteredCommands.length > 0) {
      setAnnouncement(`${filteredCommands.length} commands available.`);
    } else {
      setAnnouncement("No matching commands.");
    }
  }, [search, filteredCommands.length]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;

      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown" && filteredCommands.length > 0) {
        e.preventDefault();
        const next = (selectedIndex + 1) % filteredCommands.length;
        setSelectedIndex(next);
        setAnnouncement(filteredCommands[next].label);
      } else if (e.key === "ArrowUp" && filteredCommands.length > 0) {
        e.preventDefault();
        const next = (selectedIndex - 1 + filteredCommands.length) % filteredCommands.length;
        setSelectedIndex(next);
        setAnnouncement(filteredCommands[next].label);
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          setAnnouncement(`Navigated to ${filteredCommands[selectedIndex].label}`);
          filteredCommands[selectedIndex].action(context);
          onClose();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, onClose, context]);

  if (!isOpen) return null;

  return (
    <div
      className="palette-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="palette-label"
    >
      <div
        className="palette-modal"
        onClick={(e) => e.stopPropagation()}
        ref={modalRef}
      >
        <h2 id="palette-label" className="sr-only">Command Palette</h2>
        <div id="palette-announcer" className="sr-only" aria-live="polite">
          {announcement}
        </div>
        <div className="palette-header">
          <span className="palette-search-icon" aria-hidden="true">/</span>
          <input
            ref={inputRef}
            type="text"
            className="palette-input"
            placeholder="Type a command..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-autocomplete="list"
            aria-controls="palette-results"
          />
          <kbd className="palette-esc">Esc</kbd>
        </div>
        <ul id="palette-results" className="palette-body" role="listbox">
          {filteredCommands.map((cmd, idx) => (
            <li
              key={cmd.id}
              className={`palette-item ${idx === selectedIndex ? "selected" : ""}`}
              role="option"
              aria-selected={idx === selectedIndex}
              onClick={() => { cmd.action(context); onClose(); }}
              onMouseEnter={() => setSelectedIndex(idx)}
            >
              <span className="palette-item-main">
                <span className="palette-item-icon" aria-hidden="true">{cmd.icon}</span>
                <span className="palette-item-label">{cmd.label}</span>
              </span>
              {cmd.shortcut && <kbd className="palette-item-shortcut">{cmd.shortcut}</kbd>}
            </li>
          ))}
          {filteredCommands.length === 0 && (
            <li className="palette-empty" role="option" aria-selected="false">No commands found</li>
          )}
        </ul>
        <div className="palette-footer">
          <div className="palette-hint">
            <span><kbd>Up/Down</kbd> navigate</span>
            <span><kbd>Enter</kbd> select</span>
          </div>
          <div className="palette-brand">Telite <span>Command</span></div>
        </div>
      </div>
    </div>
  );
}
