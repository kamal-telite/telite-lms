import { Panel, Avatar } from "../../common/ui";
import {
  getInitials,
  formatPercent,
  getScoreColor,
  getRankColor,
} from "../../../utils/formatters";

/**
 * LeaderboardSection - Cohort leaderboard display
 */
export function LeaderboardSection({ leaderboard, currentUserRank, currentUserId }) {
  return (
    <section id="section-leaderboard">
      <Panel
        title="Cohort Leaderboard"
        subtitle={`You are currently ${currentUserRank == null ? "-" : `#${currentUserRank}`} in your cohort`}
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ width: 60, textAlign: "center" }}>Rank</th>
                <th>Learner</th>
                <th style={{ textAlign: "right" }}>PAL Score</th>
                <th style={{ textAlign: "right" }}>Streak</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((row, idx) => {
                const rowId = String(row.id || idx);
                return (
                  <tr
                    key={rowId}
                    className={rowId === String(currentUserId) ? "is-highlighted" : ""}
                  >
                    <td
                      style={{
                        textAlign: "center",
                        fontWeight: 700,
                        color: getRankColor(row.rank),
                      }}
                    >
                      #{row.rank}
                    </td>
                    <td>
                      <div
                        className="leaderboard-row"
                        style={{ padding: 0, borderBottom: 0 }}
                      >
                        <Avatar
                          initials={getInitials(row.full_name)}
                          size={24}
                        />
                        <span>{row.full_name}</span>
                      </div>
                    </td>
                    <td
                      className="mono"
                      style={{
                        textAlign: "right",
                        color: getScoreColor(row.pal_score),
                        fontWeight: 700,
                      }}
                    >
                      {formatPercent(row.pal_score)}
                    </td>
                    <td
                      className="mono"
                      style={{
                        textAlign: "right",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {row.streak_days}d
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </section>
  );
}
