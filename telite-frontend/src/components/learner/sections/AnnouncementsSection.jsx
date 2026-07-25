import { Button, Panel, Badge, EmptyState, LoadingState, ErrorState } from "../../common/ui";
import { formatMonthDate } from "../../../utils/formatters";

/**
 * AnnouncementsSection - View and manage announcements
 */
export function AnnouncementsSection({
  announcements,
  onMarkRead,
}) {
  const { items, loading, error } = announcements;

  return (
    <section id="section-announcements">
      <Panel
        title="Announcements"
        subtitle="Updates from your organization"
      >
        {loading ? (
          <LoadingState
            title="Loading announcements..."
            body="Checking the latest messages."
          />
        ) : error ? (
          <ErrorState
            body={error}
            action={
              <Button tone="primary" onClick={() => window.location.reload()}>
                Retry
              </Button>
            }
          />
        ) : items.length === 0 ? (
          <EmptyState
            title="No announcements yet"
            body="Organization announcements will appear here."
          />
        ) : (
          <div className="dashboard-stack">
            {items.map((announcement) => (
              <article className="soft-card" key={announcement.id}>
                <div
                  className="split-actions"
                  style={{ alignItems: "flex-start" }}
                >
                  <div>
                    <div className="row-title">{announcement.title}</div>
                    <div className="row-subtitle">
                      {announcement.published_at
                        ? formatMonthDate(announcement.published_at)
                        : "Published"}
                    </div>
                  </div>
                  <Badge tone={announcement.is_read ? "neutral" : "brand"}>
                    {announcement.is_read ? "Read" : "Unread"}
                  </Badge>
                </div>
                <p className="muted" style={{ marginTop: 12 }}>
                  {announcement.body}
                </p>
                {!announcement.is_read ? (
                  <div style={{ marginTop: 14 }}>
                    <Button
                      size="small"
                      tone="primary"
                      onClick={() => onMarkRead(announcement.id)}
                    >
                      Mark read
                    </Button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </Panel>
    </section>
  );
}
