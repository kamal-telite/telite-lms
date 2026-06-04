# Telite LMS Frontend/UI Fix Context

Last updated: 2026-05-23

## User Intent

- Improve the frontend/UI across the project without breaking existing website behavior.
- Fix actual frontend/UI errors one by one.
- Keep the theme, fonts, styles, buttons, dashboards, and pages consistent and professional.
- Maintain this file as the persistent context and update it whenever a successful website change is made.

## Explicitly Out Of Scope For Now

- The landing page "Contact sales" button is for a future feature. Leave it as-is.
- The landing page "Book a demo" button is for a future feature. Leave it as-is.

## Current Baseline

- Frontend path: `telite-frontend`
- App framework: Vite + React
- Build command checked: `npm run build`
- Current build status before fixes: passes, with a large chunk warning only.
- Existing modified file before this work began: `telite-frontend/package-lock.json`
- Important safety rule: do not revert unrelated existing changes.

## Audit Findings To Address

1. Icon name mismatches cause fallback icons.
   - `DashboardLayout.jsx` uses `chevron-left`, but `icons.jsx` defines `chevronRight`.
   - Some pages use `close`, but `icons.jsx` defines `x`.

2. Multiple competing design systems reduce UI continuity.
   - Global dashboard CSS uses Geist/Geist Mono.
   - Landing and platform admin use Tailwind utility classes.
   - Platform admin additionally uses Inter, Space Grotesk, Material Symbols, and its own scoped CSS.

3. Tailwind content paths are stale.
   - `tailwind.config.js` references old page paths such as `./src/pages/LandingPage.jsx`.
   - Actual paths are nested under folders like `src/pages/landing/LandingPage.jsx`.

4. Theme token gap.
   - `AcceptInvitePage.jsx` uses `data-theme="brand"`.
   - `global.css` defines `super`, `ats`, `stats`, and `learner`, but not `brand`.

5. Undefined CSS variable usage.
   - Several files use `var(--danger)`.
   - The declared token is `--red`, not `--danger`.

6. Encoding corruption appeared in PowerShell output, but direct UTF-8 inspection shows the React source contains valid characters.
   - Checked signup and landing strings with Node.
   - No UI code change needed for this item unless a browser screenshot later shows real mojibake.

7. Shared `Button` component ignores unsupported props.
   - Pages pass `size="small"`, but `Button` does not implement a size variant.

8. Platform admin has many placeholder buttons.
   - Many filter/export/pagination/log/support buttons are styled as active controls but do not perform actions.
   - Some of these should be wired; others may need to be made visibly disabled or converted to non-button UI.

9. Platform admin visual language is inconsistent with the rest of the app.
   - It uses glass/neumorphic styling, large rounded corners, Material Symbols, hardcoded fallback data, and different density.

10. Platform admin contains stale hardcoded display data.
   - Example: fixed date "October 24, 2023".

11. Responsive continuity risk.
   - Platform admin uses `h-screen`, `w-screen`, and `overflow-hidden`, which can clip smaller screens.

12. Bundle size warning.
   - Build emits a warning for a JS chunk larger than 500 kB.
   - This is not a functional error, but route-level code splitting may be useful later.

## Change Log

- 2026-05-20: Created this `context.md` file to preserve audit context and track fixes.
- 2026-05-20: Completed first low-risk frontend stability batch and verified with `npm run build`.
  - Added `data-theme="brand"` support in `global.css` for accept-invite pages.
  - Added `--danger` as an alias for the existing red token so current UI color references resolve.
  - Added `btn--small` / `btn--sm` styling and updated `Button` to consume the `size` prop instead of passing it through to the DOM.
  - Added icon aliases for `chevron-left`, `chevron-right`, `chevronLeft`, and `close` so existing icon calls render correctly.
  - Updated Tailwind content scanning to include nested page files under `src/pages`.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-20: Re-checked the apparent encoding issue using Node UTF-8 reads.
  - Finding corrected: the mojibake seen in shell output is a PowerShell display/codepage artifact, not bad React source.
  - No source edits made for encoding.
- 2026-05-20: Completed first platform-admin interaction batch and verified with `npm run build`.
  - Topbar notification and app-switcher buttons now show explicit feedback instead of doing nothing.
  - Floating add button now routes to `/platform-admin/organizations`.
  - Organization tab filters now work locally for all/college/company/inactive.
  - Organization export now downloads CSV for the current filtered rows.
  - Organization view action now shows useful row detail instead of being inert.
  - Single-page organization pagination controls are now disabled to avoid fake paging.
  - Admin Control tabs now switch between super admins, organization admins, and pending invitations.
  - Admin export now downloads CSV for the active tab.
  - Admin reset/delete placeholders now show explicit feedback instead of silently doing nothing.
  - Security Audit "View Detailed Log" now routes to Audit Logs.
  - Invite "Remind All" now gives feedback based on pending invite count.
  - Audit Logs export now downloads CSV.
  - Audit Logs refresh now reloads data.
  - Single-page audit pagination controls are now disabled to avoid fake paging.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-20: Reworked platform overview data display and verified with `npm run build`.
  - Replaced stale hardcoded date with the current local date.
  - Replaced fake active session and last-check text with live managed-user count and current check time.
  - Replaced hardcoded KPI fallbacks like `1,284`, `432`, and `2.4M` with real backend values or `0`.
  - Replaced hardcoded recent organizations with the backend `org_usage` data.
  - Replaced hardcoded live activity items with backend `recent_activity` data.
  - Replaced hardcoded Moodle sync status with backend `moodle_health` counts and a computed sync percentage.
  - Wired the overview "Sync Now" button to the existing platform Moodle sync API.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-20: Removed platform-admin decorative background blobs and verified with `npm run build`.
  - Removed fixed blurred background decorations from the platform-admin page wrapper.
  - This keeps the page visually cleaner and closer to the restrained dashboard style.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-20: Completed Moodle Sync, Feature Flags, and Help button behavior batch and verified with `npm run build`.
  - Moodle Sync tenant mapping now has a real status filter.
  - Moodle Sync tenant mapping now exports the currently visible rows to CSV.
  - Moodle Sync empty filtered states now display a useful empty row.
  - Moodle Sync "View Detailed Log" now gives explicit context instead of doing nothing.
  - Feature Flags "Export Report" now downloads CSV.
  - Feature Flags "Re-sync All" now reloads feature flag data.
  - Help page documentation/tutorial/support buttons now provide explicit feedback.
  - Help page support actions and changelog button now provide explicit feedback.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-20: Completed Analytics placeholder-control batch and verified with `npm run build`.
  - Analytics export now downloads a CSV export of the currently displayed metrics, and the button label was corrected to "Export CSV".
  - Analytics "Live Monitor" now gives explicit feedback that live monitor is not connected yet.
  - Analytics table filter now gives explicit feedback instead of doing nothing.
  - Analytics table row action buttons now give explicit feedback instead of doing nothing.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-22: Completed platform-admin shell consistency and responsive clipping batch and verified with `npm.cmd run build`.
  - Platform admin scoped font tokens now use the shared Geist / Geist Mono stack instead of Inter and Space Grotesk.
  - Removed negative letter-spacing from platform-admin scoped heading/data text tokens.
  - Relaxed the platform-admin root/main full-viewport overflow lock so pages can scroll naturally.
  - Added mobile overrides so the fixed sidebar becomes a normal full-width section below 900px and no longer forces content off-screen.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-22: Completed platform-admin visual continuity cleanup and verified with `npm.cmd run build`.
  - Replaced scoped glass/neumorphic panel treatments with solid surfaces, standard borders, and subtle shadows.
  - Reduced oversized platform-admin panel/card radii to 8px while leaving true circular controls and pills intact.
  - Replaced dramatic tilt/3D hover motion with restrained one-pixel lift states.
  - Simplified inset input shadows to match the quieter dashboard visual language.
  - Removed remaining decorative blurred modal background blobs from the admin invite dialog.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-22: Completed Audit Logs filter behavior batch and verified with `npm.cmd run build`.
  - Audit date range, target type, severity, and search controls now filter the loaded log rows locally.
  - Audit target filter now derives real target types from loaded log data instead of showing a fake organization selector.
  - Audit export now downloads the currently filtered rows instead of always exporting every loaded log.
  - Audit empty state and footer counts now reflect active filters.
  - Removed the unsupported Critical severity option because current backend audit rows emit `WARN` and `INFO`.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-22: Replaced hardcoded Audit Logs summary cards with live filtered audit data and verified with `npm.cmd run build`.
  - Audit summary cards now show warning count, visible event count, and unique actor count from the currently filtered rows.
  - Audit summary progress bars now derive from loaded/filtered log totals instead of fixed percentages.
  - Audit row status icons now show a warning icon for `WARN` rows and a check icon for normal info rows.
  - Removed stale hardcoded text such as fixed security alert counts, throughput counts, and active session counts.
  - Build result: passes. The existing large JS chunk warning remains.
- 2026-05-23: Completed learner page contract/alignment fixes and verified with `npm.cmd run build`.
  - Learner courses now normalize progress from future `completion_pct` or current backend `progress`.
  - Learner course status now prefers `progress_status` while retaining fallback support for future/current `status` fields.
  - Resume Course buttons now disable gracefully when no active course is assigned.
  - Notification drawer now uses shared icon button styling and supports both `message` and backend `body` fields.
  - PAL dimensions now match the backend scoring weights and include time-on-task and streak dimensions.
  - Leaderboard and course filters now render useful empty states.
  - Backend task submission now checks that a learner can access the task before marking it submitted.
  - Build result: passes. Backend syntax check `python -m py_compile telite-backend/app/services/store.py` passes. Full backend pytest could not run because pytest is not installed in this Python environment.
- 2026-05-23: Completed shared sidebar, learner label, and admin learner-delete permission batch.
  - Shared dashboard sidebars now use an icon-only collapse control in the top-right of the sidebar header.
  - Removed the duplicate profile block from the sidebar because profile access already exists in the top navigation.
  - Renamed the learner "Moodle link" navigation label to "Course Link".
  - Admin-level deletion now uses the admin dependency instead of super-admin-only access.
  - Category admins can delete learners only inside their own category scope; broader user deletion remains blocked for category admins.
  - Build result: `npm.cmd run build` passes after running outside the sandbox because Vite config loading hit a sandbox read restriction. The existing large JS chunk warning remains.
  - Backend syntax check passes using bundled Python: `python.exe -c py_compile ... management.py`.
- 2026-05-23: Completed admin learner-info layout and small button-label continuity batch.
  - Category Admin learner management now uses responsive learner cards instead of the cramped multi-column table.
  - Learner rows now group identity, course progress, PAL score, enrollment type, status, and actions consistently with shared dashboard UI primitives.
  - Learner filters/actions use a scoped toolbar and the shared plus-icon primary button style.
  - Admin export menu labels were cleaned from corrupted emoji text to plain "Download CSV" and "Download PDF".
  - Build result: `npm.cmd run build` passes. The existing large JS chunk warning remains.
- 2026-05-23: Completed SuperAdmin dead-action cleanup.
  - Removed a non-functional "View all" action from the enrollment audit panel.
  - Updated the PAL "Full report" action to route to the first available category report instead of hardcoding the ATS category; it now shows a warning toast if no category exists.
  - Build result: `npm.cmd run build` passes. The existing large JS chunk warning remains.
- 2026-05-23: Completed Admin/SuperAdmin/Learner profile UI continuity batch.
  - Reworked the shared Admin/SuperAdmin profile settings route into a two-column profile layout with consistent panel padding, dashboard fonts, shared icons, and tokenized button styling.
  - Normalized profile route tabs so `tab=profile` and other unknown profile tab values open the General profile panel instead of rendering an empty Settings shell.
  - Replaced broken emoji text in the profile dropdown with shared SVG icons and consistent menu button dimensions.
  - Added learner profile edit mode with editable full name/email fields, read-only category/enrollment fields, and matching Save/Cancel/Edit button styles.
  - Build result: `npm.cmd run build` passes. The existing large JS chunk warning remains.
  - Browser visual attach could not complete in this environment because the browser runtime hit a local `AppData` permission error; use the local dev server for final visual QA.
- 2026-05-23: Completed padding-only continuity cleanup across dashboard panels, tables, forms, and modals.
  - Added shared padding compatibility for older `panel-header`, `panel-body`, `panel-footer`, `panel-title`, and `panel-subtitle` classes so older tabs match the newer `Panel` component spacing.
  - Standardized table cell horizontal padding and minimum table width to stop text/progress values from touching or spilling past holder borders.
  - Standardized form grid gaps and minimum widths so inputs/selects/radio chips stay inside their containers.
  - Adjusted modal header/content/footer padding and scrolling so modal footer buttons no longer overlap form fields or detail cards.
  - No feature behavior was changed.
  - Build result: `npm.cmd run build` passes. The existing large JS chunk warning remains.
- 2026-05-24: Completed targeted modal footer visibility and leaderboard rank alignment fixes.
  - Modal content now reserves bottom space and the shared modal footer has a subtle top shadow plus consistent button minimum width, making Add Learner and Add Category submit buttons visible while preserving project styling.
  - Admin PAL leaderboard rank numbers now use a fixed-width centered numeric cell, so ranks align consistently.
  - No feature behavior was changed.
  - Build result: `npm.cmd run build` passes. The existing large JS chunk warning remains.
- 2026-05-24: Completed modal portal primary-button visibility fix.
  - Add Learner and Add Category modal primary buttons were present but invisible because modal portals render outside the dashboard `data-theme`, leaving `--theme-accent` undefined.
  - Added brand-token fallbacks for primary buttons and scoped modal portal theme tokens so submit buttons render visibly while keeping the existing style.
  - Build result: `npm.cmd run build` passes. The existing large JS chunk warning remains.
- 2026-05-24: Fixed Add Learner 500 error caused by duplicate name-derived learner IDs.
  - Manual learner creation no longer uses only `user-{slugified full name}` for new learner IDs when the email is new.
  - New learner IDs and usernames are now generated with collision-safe suffixes, while existing learners are still matched and updated by email.
  - Applied the same collision-safe generation to self-enrollment approval because it creates learner users through the same name-derived pattern.
  - Backend syntax check passes for `telite-backend/app/services/store.py` using bundled Python.
- 2026-05-24: Fixed Add Category 500 error in SuperAdmin portal.
  - Category creation SQL listed 15 columns but only 14 placeholders, causing `sqlite3.OperationalError` and a 500 on submit.
  - Corrected the insert placeholder count in `create_category`.
  - Direct backend reproduction against a temporary SQLite DB now succeeds for Add Learner, same-name learner collision, and Add Category.
  - Backend syntax check passes for `telite-backend/app/services/store.py` using bundled Python.

## Next Planned Fix Order

1. Fix low-risk token/icon issues:
   - Add missing `brand` theme.
   - Add `--danger` alias or replace usages with `--red`.
   - Add icon aliases for names currently used by pages.

2. Fix shared component mismatch:
   - Add supported `Button` size variants so existing `size="small"` props work.

3. Clean visible encoding corruption carefully.
   - Start with user-facing strings in React components.
   - Avoid sweeping backend/comment-only changes unless needed for UI.

4. Correct Tailwind content paths.

5. Review platform admin placeholder controls.
   - Leave "Contact sales" and "Book a demo" alone.
   - For other controls, either wire behavior safely or disable/clarify inactive controls without breaking layout.

6. Re-run `npm run build` after each small batch of changes.
