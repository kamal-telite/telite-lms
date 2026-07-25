import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export function useKeyboardShortcuts({ 
  searchRef, 
  toggleSidebar, 
  triggerGlobalSync, 
  pathname, 
  settingsState, 
  showToast,
  onCreateOrg,
  onInviteAdmin,
  onExportAudit
}) {
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e) => {
      const mod = e.metaKey || e.ctrlKey;
      const shift = e.shiftKey;
      const alt = e.altKey;

      // ⌘K - Focus search
      if (mod && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchRef.current?.focus();
      }
      // ⌥N - New Organization
      if (alt && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        navigate('/platform-admin/organizations');
        onCreateOrg?.();
      }
      // ⌥I - Send Invitation
      if (alt && e.key.toLowerCase() === 'i') {
        e.preventDefault();
        navigate('/platform-admin/admins');
        onInviteAdmin?.();
      }
      // ⇧E - Export Audit Log
      if (shift && e.key.toUpperCase() === 'E') {
        e.preventDefault();
        navigate('/platform-admin/audit');
        onExportAudit?.();
      }
      // ⌘\ - Toggle Sidebar
      if (mod && e.key === '\\') {
        e.preventDefault();
        toggleSidebar();
      }
      // ⌘S - Save settings (if on Settings tab)
      if (mod && !shift && e.key.toLowerCase() === 's') {
        if (pathname.endsWith('/settings')) {
          e.preventDefault();
          showToast(`Settings saved successfully — Platform: "${settingsState.platformName}"`, 'success');
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [navigate, toggleSidebar, triggerGlobalSync, pathname, settingsState, showToast, onCreateOrg, onInviteAdmin, onExportAudit]);
}
