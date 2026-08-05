import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, Icon, Panel, useToast } from "./ui";
import {
  fetchNotificationPreferences,
  updateNotificationPreference,
} from "../../services/client";
import "../../styles/components/notif-prefs.css";

const CATEGORY_ORDER = [
  "tasks",
  "assignments",
  "courses",
  "announcements",
  "messages",
  "security",
  "system",
  "marketing",
];

const CATEGORY_COPY = {
  tasks: { title: "Tasks", desc: "Assigned tasks, status changes, and review outcomes." },
  assignments: { title: "Assignments", desc: "Submitted work, grading feedback, and revision requests." },
  courses: { title: "Courses", desc: "Enrollment, publishing, course progress, and completion updates." },
  announcements: { title: "Announcements", desc: "Category and organization announcements." },
  messages: { title: "Messages", desc: "Direct messages, mentions, and conversation updates." },
  security: { title: "Security", desc: "Critical account and access alerts." },
  system: { title: "System", desc: "Platform, workspace, and account administration updates." },
  marketing: { title: "Marketing", desc: "Product news, newsletters, and promotional updates." },
};

const DEFAULT_PREFERENCES = CATEGORY_ORDER.map((category) => ({
  category,
  channel_in_app: true,
  channel_email: true,
  is_critical: category === "security",
  source: category === "security" ? "critical" : "system",
}));

const CHANNEL_LABELS = {
  channel_in_app: "In-App",
  channel_email: "Email",
};

function orderPreferences(items) {
  const byCategory = new Map(items.map((item) => [item.category, item]));
  return CATEGORY_ORDER.map((category) => {
    const resolved = byCategory.get(category) || DEFAULT_PREFERENCES.find((item) => item.category === category);
    return {
      ...resolved,
      channel_in_app: category === "security" ? true : Boolean(resolved.channel_in_app),
      channel_email: category === "security" ? true : Boolean(resolved.channel_email),
      is_critical: category === "security" ? true : Boolean(resolved.is_critical),
    };
  });
}

function PreferenceSkeleton() {
  return (
    <div className="notif-prefs-skeleton" aria-label="Loading notification preferences">
      {CATEGORY_ORDER.slice(0, 6).map((category) => (
        <div className="notif-prefs-skeleton__row" key={category}>
          <div className="notif-prefs-skeleton__copy">
            <span className="notif-prefs-skeleton__line notif-prefs-skeleton__line--title" />
            <span className="notif-prefs-skeleton__line notif-prefs-skeleton__line--body" />
          </div>
          <span className="notif-prefs-skeleton__switch" />
          <span className="notif-prefs-skeleton__switch" />
        </div>
      ))}
    </div>
  );
}

function PreferenceSwitch({ category, channel, checked, disabled, saving, onToggle }) {
  const info = CATEGORY_COPY[category] || { title: category, desc: "" };
  const channelLabel = CHANNEL_LABELS[channel];
  const disabledReason = "Security notifications are mandatory and cannot be disabled.";
  const ariaLabel = `${channelLabel} notifications for ${info.title}`;
  const tooltipId = `${category}-${channel}-notification-tooltip`;

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      aria-describedby={disabled ? tooltipId : undefined}
      className={`notif-prefs-switch${checked ? " is-on" : ""}${disabled ? " is-disabled" : ""}${saving ? " is-saving" : ""}`}
      disabled={disabled || saving}
      title={disabled ? disabledReason : ariaLabel}
      onClick={() => onToggle(category, channel, checked)}
    >
      <span className="notif-prefs-switch__thumb" />
    </button>
  );
}

export function NotificationPreferencesPanel() {
  const { showToast } = useToast();
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingKeys, setSavingKeys] = useState(() => new Set());

  const loadPreferences = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const payload = await fetchNotificationPreferences();
      setPreferences(orderPreferences(Array.isArray(payload) && payload.length ? payload : DEFAULT_PREFERENCES));
    } catch {
      setError("Unable to load notification preferences.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError("");
      try {
        const payload = await fetchNotificationPreferences();
        if (!cancelled) {
          setPreferences(orderPreferences(Array.isArray(payload) && payload.length ? payload : DEFAULT_PREFERENCES));
        }
      } catch {
        if (!cancelled) {
          setError("Unable to load notification preferences.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const visiblePreferences = useMemo(() => orderPreferences(preferences), [preferences]);

  async function handleToggle(category, channel, currentValue) {
    const previous = visiblePreferences;
    const nextValue = !currentValue;
    const savingKey = `${category}:${channel}`;

    setSavingKeys((current) => new Set(current).add(savingKey));
    setPreferences((current) =>
      orderPreferences(current).map((pref) =>
        pref.category === category ? { ...pref, [channel]: nextValue } : pref
      )
    );

    try {
      const updated = await updateNotificationPreference(category, { [channel]: nextValue });
      setPreferences((current) =>
        orderPreferences(current).map((pref) =>
          pref.category === category ? { ...pref, ...updated } : pref
        )
      );
    } catch {
      setPreferences(previous);
      showToast("Failed to update notification preference.", "error");
    } finally {
      setSavingKeys((current) => {
        const next = new Set(current);
        next.delete(savingKey);
        return next;
      });
    }
  }

  return (
    <Panel
      title="Notification Preferences"
      subtitle="Manage how you receive updates"
      className="notif-prefs-panel"
    >
      {isLoading ? <PreferenceSkeleton /> : null}

      {!isLoading && error ? (
        <div className="notif-prefs-state" role="alert">
          <div>
            <h4>Unable to load notification preferences.</h4>
            <p>Check your connection and try again.</p>
          </div>
          <Button tone="primary" size="small" onClick={loadPreferences}>
            Retry
          </Button>
        </div>
      ) : null}

      {!isLoading && !error ? (
        <div className="notif-prefs-container">
          <div className="notif-prefs-header" aria-hidden="true">
            <span>Category</span>
            <span>In-App</span>
            <span>Email</span>
          </div>

          <div className="notif-prefs-list" role="list" aria-label="Notification preferences">
            {visiblePreferences.map((pref) => {
              const info = CATEGORY_COPY[pref.category] || { title: pref.category, desc: "" };
              const isLocked = pref.is_critical || pref.category === "security";

              return (
                <div className="notif-prefs-row" role="listitem" key={pref.category}>
                  <div className="notif-prefs-copy">
                    <div className="notif-prefs-title-row">
                      <h4 className="notif-prefs-title">{info.title}</h4>
                      {isLocked ? (
                        <span className="notif-prefs-lock">
                          <Icon name="lock" size={14} />
                          <span
                            id={`${pref.category}-channel_in_app-notification-tooltip`}
                            role="tooltip"
                            className="notif-prefs-tooltip"
                          >
                            Security notifications are mandatory and cannot be disabled.
                          </span>
                        </span>
                      ) : null}
                    </div>
                    <p className="notif-prefs-desc">{info.desc}</p>
                  </div>

                  <div className="notif-prefs-channel" data-label="In-App">
                    <PreferenceSwitch
                      category={pref.category}
                      channel="channel_in_app"
                      checked={pref.channel_in_app}
                      disabled={isLocked}
                      saving={savingKeys.has(`${pref.category}:channel_in_app`)}
                      onToggle={handleToggle}
                    />
                  </div>

                  <div className="notif-prefs-channel" data-label="Email">
                    {isLocked ? (
                      <span
                        id={`${pref.category}-channel_email-notification-tooltip`}
                        role="tooltip"
                        className="notif-prefs-sr-only"
                      >
                        Security notifications are mandatory and cannot be disabled.
                      </span>
                    ) : null}
                    <PreferenceSwitch
                      category={pref.category}
                      channel="channel_email"
                      checked={pref.channel_email}
                      disabled={isLocked}
                      saving={savingKeys.has(`${pref.category}:channel_email`)}
                      onToggle={handleToggle}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </Panel>
  );
}
