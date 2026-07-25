import { Panel, EmptyState } from "../../common/ui";

/**
 * SettingsSection - Account settings (placeholder for future features)
 */
export function SettingsSection() {
  return (
    <section id="section-settings">
      <Panel title="Account Settings" subtitle="Personalize your workspace">
        <EmptyState
          title="Settings coming soon"
          body="Theme toggles, notifications, and privacy options will be available here."
        />
      </Panel>
    </section>
  );
}
