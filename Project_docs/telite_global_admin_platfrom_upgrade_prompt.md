# 🎯 MASTER ENGINEERING PROMPT
## Telite LMS — Global Admin Console: Full UI/UX + Functionality Upgrade
### Roles: Prompt Engineer · Design Engineer · Full-Stack Engineer
### Stack: Next.js / React · Tailwind CSS · shadcn/ui · Zustand · React Hook Form

---

## 📸 SOURCE ANALYSIS — What We See, What's Broken

From the 7 screenshots provided, the following problems are confirmed:

| Area | Issue | Severity |
|---|---|---|
| Sidebar | Dark navy `#1e1b4b` — text/icons barely visible against it | High |
| Sidebar | No toggle — always expanded, takes permanent space | High |
| Sidebar | Logo has an icon circle before "Telite LMS" — must be removed | Medium |
| Layout | All pages render zoomed in — elements too large for viewport | High |
| Top bar | Search field is placeholder-only — no filtering logic | High |
| Top bar | Bell/notification button does nothing | High |
| Top bar | Grid/apps button does nothing | High |
| Dashboard | FAB (+) button at bottom-right is a placeholder | Medium |
| Dashboard | "Sync Now" button fires no action | High |
| Organizations | "New Organization" modal clips behind the top bar | Critical |
| Organizations | Filter, Export CSV buttons non-functional | High |
| Organizations | All/Colleges/Companies/Inactive tab pills non-functional | High |
| Organizations | View (eye) and Suspend buttons on org rows non-functional | High |
| Admin Control | Send Invite button missing entirely | High |
| Admin Control | Filter + Download icon buttons non-functional | High |
| Admin Control | Super Admins/All Org Admins/Pending Invitations tabs non-functional | High |
| Admin Control | Row-level action buttons (suspend, delete, restore) non-functional | High |

---

## 🗂️ TASK BREAKDOWN — 8 Isolated Engineering Tasks

Each task is self-contained. Execute in order. Each has: Goal → Acceptance Criteria → Implementation Spec.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TASK 1 — Global Layout & Scale Fix
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Goal
The entire admin console appears zoomed in. The sidebar occupies 240px of a 1280px viewport making everything cramped. Font sizes, spacing, and card sizes need scaling down to a standard enterprise admin density.

### Root Cause
The Tailwind config or body CSS is likely using `font-size: 16px` base with `lg:` breakpoints that target 1280px+. On a 1280px browser window, breakpoint-sensitive padding and font scale feels large.

### Acceptance Criteria
- [ ] Sidebar width: **220px** (down from 240px)
- [ ] Main content area: properly fills the remaining viewport without overflow
- [ ] Base font size: `13px` for table rows, `12px` for labels, `14px` for body copy
- [ ] Card padding: `16px` internal (not `24px`)
- [ ] Page header ("Admin Control", "Organizations") font: `28px` (down from current ~40px)
- [ ] Top bar height: `52px`
- [ ] No horizontal scroll at `1280px` viewport width
- [ ] Sidebar section labels ("CORE SECTION", "INSIGHTS SECTION") at `10px` uppercase spaced

### Implementation Spec

**globals.css / tailwind.config.js:**
```css
/* Override body base so everything scales correctly */
html { font-size: 14px; }

/* Sidebar */
.sidebar { width: 220px; min-width: 220px; }

/* Main content offset */
.main-content { margin-left: 220px; }

/* Top bar */
.topbar { height: 52px; }
```

**Tailwind config:**
```js
// In tailwind.config.js extend spacing
spacing: {
  'sidebar': '220px',
  'topbar': '52px',
}
```

**Page titles:**
```jsx
// Replace text-4xl / text-5xl headings with:
<h1 className="text-2xl font-bold text-gray-900 tracking-tight">Admin Control</h1>
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TASK 2 — Sidebar: Design Overhaul + Toggle
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Goal
Replace the dark, hard-to-read sidebar with a clean, minimal, professional sidebar. Remove the icon before the logo. Add a collapse/expand toggle. Fix color contrast throughout.

### Acceptance Criteria
- [ ] Sidebar background: `#FFFFFF` (white) with a `1px solid #E5E7EB` right border
- [ ] Active nav item: `bg-indigo-50 text-indigo-700 font-semibold rounded-lg`
- [ ] Inactive nav item: `text-gray-600 hover:bg-gray-50 hover:text-gray-900`
- [ ] Section labels: `text-[10px] font-semibold text-gray-400 uppercase tracking-widest`
- [ ] Logo: text only — **"Telite LMS"** in `font-semibold text-gray-900 text-[15px]`, no icon/circle
- [ ] Below logo name: `"GLOBAL ADMIN CONSOLE"` in `text-[10px] text-gray-400 tracking-widest uppercase`
- [ ] Toggle button: hamburger icon (☰) at top-right corner of sidebar
  - Click → sidebar collapses to `56px` width showing only icons
  - Click again → expands back to `220px` showing icons + labels
  - Transition: `transition-all duration-200 ease-in-out`
- [ ] Collapsed state: icons only, tooltip on hover showing the label
- [ ] Bottom of sidebar: "Logout" link `text-gray-500 hover:text-red-600`
- [ ] Nav items use Material Symbols icons (already imported) at `20px`

### Colour Palette for Sidebar
```
Background:      #FFFFFF
Right border:    #E5E7EB
Logo text:       #111827
Section labels:  #9CA3AF
Inactive items:  #4B5563  (hover: #111827)
Active bg:       #EEF2FF  (indigo-50)
Active text:     #4338CA  (indigo-700)
Active border:   2px left border #4648D4
```

### Component Spec (React/JSX)

```jsx
// sidebar/Sidebar.tsx
const [collapsed, setCollapsed] = useState(false);

<aside className={cn(
  "fixed left-0 top-0 h-full bg-white border-r border-gray-200 z-50 flex flex-col transition-all duration-200",
  collapsed ? "w-14" : "w-[220px]"
)}>

  {/* Header */}
  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
    {!collapsed && (
      <div>
        <p className="text-[15px] font-semibold text-gray-900 leading-tight">Telite LMS</p>
        <p className="text-[10px] text-gray-400 uppercase tracking-widest mt-0.5">Global Admin Console</p>
      </div>
    )}
    <button onClick={() => setCollapsed(!collapsed)}
      className="p-1.5 rounded-md hover:bg-gray-100 text-gray-500 ml-auto">
      <MenuIcon size={18} />
    </button>
  </div>

  {/* Nav sections */}
  {NAV_SECTIONS.map(section => (
    <div className="px-3 py-2">
      {!collapsed && (
        <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest px-2 mb-1">
          {section.label}
        </p>
      )}
      {section.items.map(item => (
        <NavItem key={item.href} item={item} collapsed={collapsed} />
      ))}
    </div>
  ))}

  {/* Footer */}
  <div className="mt-auto border-t border-gray-100 px-3 py-3">
    <NavItem item={logoutItem} collapsed={collapsed} />
  </div>
</aside>
```

### Nav Item Component
```jsx
// NavItem with active state, tooltip when collapsed
function NavItem({ item, collapsed }) {
  const isActive = usePathname().startsWith(item.href);
  return (
    <Tooltip content={item.label} disabled={!collapsed}>
      <Link href={item.href}
        className={cn(
          "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] font-medium transition-all",
          isActive
            ? "bg-indigo-50 text-indigo-700 border-l-2 border-indigo-600"
            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
          collapsed && "justify-center px-2"
        )}>
        <item.icon size={18} />
        {!collapsed && <span>{item.label}</span>}
      </Link>
    </Tooltip>
  );
}
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TASK 3 — Top Bar: Working Search + Notifications + Apps
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Goal
Make the search bar actually search across orgs/admins, make the bell show real notifications, and give the grid button a useful quick-links panel.

### Acceptance Criteria

**Search Bar:**
- [ ] On keystroke → filters the visible list in the current active page
  - On Organizations page: filters org rows by name, domain, type
  - On Admin Control page: filters admin rows by name, email, org
  - On Dashboard: shows a dropdown with matching results from both categories
- [ ] Keyboard: `⌘K` or `Ctrl+K` focuses the search bar from anywhere
- [ ] Minimum 2 characters to trigger filter
- [ ] Clear button (×) when input has value
- [ ] No results state: "No results for '{query}'"
- [ ] Dropdown appears below the search bar with grouped results (Orgs, Admins)

**Notification Bell:**
- [ ] Shows a red badge dot when there are unread notifications
- [ ] Click → opens a `280px` wide dropdown panel anchored below the bell
- [ ] Panel shows a list of notification items (read from a `notifications[]` state)
- [ ] Each notification: icon + title + relative time
- [ ] "Mark all as read" button at top of panel
- [ ] "View all" link at bottom
- [ ] Click outside → closes the panel

```jsx
// notifications state (seed data)
const notifications = [
  { id: 1, type: 'sync', title: 'Moodle Sync Started', sub: 'Auto-sync for Oxford Academy', time: '15m ago', read: false },
  { id: 2, type: 'security', title: 'Security Alert', sub: 'Failed login on Admin Console', time: '45m ago', read: false },
  { id: 3, type: 'user', title: 'New User Registered', sub: 'John Doe joined Stanford University', time: '2m ago', read: true },
];
```

**Grid/Apps Button:**
- [ ] Click → opens a `240px` popover with 4 quick-link tiles:
  - Analytics · Audit Logs · Feature Flags · Settings
- [ ] Each tile: icon + label, clicking navigates to that route
- [ ] Click outside → closes

### Implementation Spec

```jsx
// TopBar.tsx
// Search: controlled input connected to useSearch() hook
// The hook exposes a `setQuery()` and `results` that other pages read via context

const { query, setQuery, results } = useSearch();

<div className="relative">
  <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
  <input
    value={query}
    onChange={e => setQuery(e.target.value)}
    placeholder="Global search..."
    className="pl-8 pr-8 py-1.5 text-sm bg-gray-50 border border-gray-200 rounded-lg w-64 
               focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
  />
  {query && (
    <button onClick={() => setQuery('')} className="absolute right-2.5 top-1/2 -translate-y-1/2">
      <XIcon size={13} className="text-gray-400" />
    </button>
  )}
  {/* Dropdown results */}
  {query.length >= 2 && <SearchDropdown results={results} onClose={() => setQuery('')} />}
</div>

// Global keyboard shortcut
useEffect(() => {
  const handler = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      searchRef.current?.focus();
    }
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}, []);
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TASK 4 — Dashboard: FAB + Sync Now
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Goal
Make the floating action button (+) open a quick-create menu, and make "Sync Now" trigger a real sync simulation with loading state.

### Acceptance Criteria

**FAB (+) Button:**
- [ ] Click → expands upward showing 2 sub-actions:
  - "New Organization" → navigates to `/platform-admin/organizations` and opens the New Org modal
  - "Send Invite" → opens the Send Invite modal (same one as Admin Control)
- [ ] Backdrop: slight overlay on expand
- [ ] Transition: `scale-100 opacity-100` from `scale-0 opacity-0` with `200ms ease`
- [ ] Click outside → collapses

```jsx
// FAB expand animation
const [fabOpen, setFabOpen] = useState(false);
const fabActions = [
  { label: 'New Organization', icon: BuildingIcon, action: () => { router.push('/organizations'); openOrgModal(); } },
  { label: 'Send Invite', icon: MailIcon, action: () => openInviteModal() },
];
```

**Sync Now Button (Moodle Global Sync Status strip):**
- [ ] Click → sets `isSyncing: true` state
- [ ] Button changes to: `Syncing…` with a spinning icon, disabled
- [ ] Progress bar animates from current % to 100% over 3 seconds
- [ ] After 3s: `isSyncing: false`, button resets to `Sync Now`
- [ ] Toast notification appears: "Sync completed — 100% success rate"
- [ ] Last sync timestamp updates to "Just now"

```jsx
const [isSyncing, setIsSyncing] = useState(false);

async function handleSync() {
  setIsSyncing(true);
  await new Promise(r => setTimeout(r, 3000)); // simulate
  setIsSyncing(false);
  setLastSync('Just now');
  toast.success('Moodle sync completed — 99.8% success rate');
}

<button onClick={handleSync} disabled={isSyncing}
  className="px-4 py-1.5 text-sm font-medium border border-gray-300 rounded-lg 
             hover:bg-gray-50 disabled:opacity-60 flex items-center gap-2">
  {isSyncing && <Loader2 className="animate-spin" size={14} />}
  {isSyncing ? 'Syncing…' : 'Sync Now'}
</button>
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TASK 5 — Organizations: Full Functionality
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Goal
Fix the "New Organization" modal positioning bug, wire all filter tabs, make Filter/Export functional, and wire the View/Suspend action buttons.

### 5A — Modal Positioning Fix (Critical)

**Problem:** The modal renders inside the scrollable content area, so `position: fixed` combined with a `transform` on an ancestor causes it to be clipped by the top bar.

**Fix:**
```jsx
// Move the modal to a Portal that renders at document.body level
// This bypasses any parent stacking contexts

import { createPortal } from 'react-dom';

function NewOrgModal({ open, onClose }) {
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-[200] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      {/* Modal card — always centered, never clipped */}
      <div className="relative z-10 bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        {/* Stepper + form content */}
      </div>
    </div>,
    document.body
  );
}
```

**Modal must have `z-index: 200`** — above the topbar (`z-50`) and sidebar (`z-50`).

### 5B — Filter Tabs (All / Colleges / Companies / Inactive)

```jsx
// State-driven filtering
const [activeFilter, setActiveFilter] = useState<'all' | 'college' | 'company' | 'inactive'>('all');

const filteredOrgs = useMemo(() => {
  if (activeFilter === 'all') return orgs;
  if (activeFilter === 'college') return orgs.filter(o => o.type === 'COLLEGE');
  if (activeFilter === 'company') return orgs.filter(o => o.type === 'COMPANY');
  if (activeFilter === 'inactive') return orgs.filter(o => o.status === 'INACTIVE');
}, [orgs, activeFilter]);

// Tab pill buttons
const tabs = [
  { key: 'all', label: 'All' },
  { key: 'college', label: 'Colleges' },
  { key: 'company', label: 'Companies' },
  { key: 'inactive', label: 'Inactive' },
];

tabs.map(tab => (
  <button
    key={tab.key}
    onClick={() => setActiveFilter(tab.key)}
    className={cn(
      "px-4 py-1.5 text-sm font-medium rounded-lg border transition-all",
      activeFilter === tab.key
        ? "bg-indigo-600 text-white border-indigo-600"
        : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
    )}
  >
    {tab.label}
  </button>
))
```

### 5C — Filter Panel

```jsx
// Filter button opens a popover with filter options
const [filterOpen, setFilterOpen] = useState(false);
const [filterState, setFilterState] = useState({ status: 'all', type: 'all' });

// Popover renders below the "Filter" button
<Popover open={filterOpen} onOpenChange={setFilterOpen}>
  <PopoverTrigger asChild>
    <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
      <FilterIcon size={14} /> Filter
    </button>
  </PopoverTrigger>
  <PopoverContent className="w-64 p-4 space-y-3">
    <div>
      <label className="text-xs font-medium text-gray-500">Status</label>
      <Select value={filterState.status} onValueChange={v => setFilterState(s => ({...s, status: v}))}>
        <SelectItem value="all">All statuses</SelectItem>
        <SelectItem value="active">Active</SelectItem>
        <SelectItem value="inactive">Inactive</SelectItem>
        <SelectItem value="suspended">Suspended</SelectItem>
      </Select>
    </div>
    <div>
      <label className="text-xs font-medium text-gray-500">Type</label>
      <Select value={filterState.type} onValueChange={v => setFilterState(s => ({...s, type: v}))}>
        <SelectItem value="all">All types</SelectItem>
        <SelectItem value="college">College</SelectItem>
        <SelectItem value="company">Company</SelectItem>
      </Select>
    </div>
    <div className="flex gap-2 pt-1">
      <button onClick={clearFilters} className="flex-1 text-xs text-gray-500 border rounded py-1.5">Clear</button>
      <button onClick={() => setFilterOpen(false)} className="flex-1 text-xs bg-indigo-600 text-white rounded py-1.5">Apply</button>
    </div>
  </PopoverContent>
</Popover>
```

### 5D — Export CSV

```jsx
function exportCSV(orgs) {
  const headers = ['ID', 'Name', 'Type', 'Domain', 'Status', 'Admin Count'];
  const rows = orgs.map(o => [o.id, o.name, o.type, o.domain, o.status, o.adminCount]);
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `organizations-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

<button onClick={() => exportCSV(filteredOrgs)}
  className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
  <DownloadIcon size={14} /> Export CSV
</button>
```

### 5E — View and Suspend Action Buttons

```jsx
// Each org row action buttons
<div className="flex items-center gap-1.5">
  {/* View button → navigates to org detail */}
  <button
    onClick={() => router.push(`/platform-admin/organizations/${org.id}`)}
    className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-gray-300"
    title="View organization"
  >
    <EyeIcon size={15} className="text-gray-500" />
  </button>

  {/* Suspend / Restore toggle */}
  <button
    onClick={() => handleToggleSuspend(org.id)}
    className={cn(
      "p-1.5 rounded-lg border",
      org.status === 'ACTIVE'
        ? "border-gray-200 hover:bg-red-50 hover:border-red-200 text-gray-500 hover:text-red-600"
        : "border-green-200 bg-green-50 text-green-600 hover:bg-green-100"
    )}
    title={org.status === 'ACTIVE' ? 'Suspend organization' : 'Restore organization'}
  >
    {org.status === 'ACTIVE'
      ? <BanIcon size={15} />
      : <CheckCircleIcon size={15} />
    }
  </button>
</div>

// Suspend handler — shows confirmation dialog
async function handleToggleSuspend(orgId) {
  const org = orgs.find(o => o.id === orgId);
  const confirmed = await confirm({
    title: org.status === 'ACTIVE' ? 'Suspend Organization?' : 'Restore Organization?',
    description: org.status === 'ACTIVE'
      ? `This will prevent all users at ${org.name} from logging in.`
      : `This will restore access for all users at ${org.name}.`,
    confirmLabel: org.status === 'ACTIVE' ? 'Suspend' : 'Restore',
    variant: org.status === 'ACTIVE' ? 'destructive' : 'default',
  });
  if (confirmed) {
    updateOrgStatus(orgId, org.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE');
    toast.success(`${org.name} ${org.status === 'ACTIVE' ? 'suspended' : 'restored'}`);
  }
}
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TASK 6 — Admin Control: Full Functionality
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Goal
Add the missing "Send Invitation" button, wire the 3 tabs, make filter/download work, and activate all row-level action buttons.

### 6A — Send Invitation Button (MISSING — Must Add)

**Location:** Top-right of the Admin Control page, next to the existing action buttons row.

```jsx
// Add "Send Invite" button — prominent, fills the gap visible in screenshots
<div className="flex items-center justify-between mb-4">
  <div>
    <h1 className="text-2xl font-bold text-gray-900">Admin Control</h1>
    <p className="text-sm text-gray-500 mt-0.5">Manage organization-level access and system-wide configurations.</p>
  </div>
  <button onClick={() => setInviteModalOpen(true)}
    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium 
               rounded-lg hover:bg-indigo-700 shadow-sm transition-colors">
    <UserPlusIcon size={15} />
    Send Invitation
  </button>
</div>
```

**Send Invitation Modal spec:**
```jsx
<Dialog open={inviteModalOpen} onOpenChange={setInviteModalOpen}>
  <DialogContent className="max-w-md">
    <DialogHeader>
      <DialogTitle>Send Invitation</DialogTitle>
      <DialogDescription>Invite a new admin to manage an organization.</DialogDescription>
    </DialogHeader>
    <form onSubmit={handleSubmitInvite}>
      <div className="space-y-4">
        <Field label="Email address" name="email" type="email" required placeholder="admin@university.edu" />
        <Field label="Full name" name="name" required placeholder="Dr. Priya Sharma" />
        <SelectField label="Organization" name="orgId" options={orgs.map(o => ({ value: o.id, label: o.name }))} />
        <SelectField label="Role" name="role"
          options={[
            { value: 'super_admin', label: 'Super Admin' },
            { value: 'category_admin', label: 'Category Admin' },
          ]}
        />
      </div>
      <DialogFooter className="mt-6">
        <button type="button" onClick={() => setInviteModalOpen(false)} className="btn-secondary">Cancel</button>
        <button type="submit" className="btn-primary">Send Invitation</button>
      </DialogFooter>
    </form>
  </DialogContent>
</Dialog>
```

**On submit:**
- Validates all fields
- Appends new entry to `pendingInvitations[]` state
- Switches active tab to "Pending Invitations" automatically
- Shows toast: `"Invitation sent to {email}"`

### 6B — Super Admins / All Org Admins / Pending Invitations Tabs

```jsx
const [activeTab, setActiveTab] = useState<'super_admins' | 'all_admins' | 'pending'>('super_admins');

const displayedAdmins = useMemo(() => {
  if (activeTab === 'super_admins') return admins.filter(a => a.role === 'super_admin');
  if (activeTab === 'all_admins') return admins;
  if (activeTab === 'pending') return pendingInvitations;
}, [admins, pendingInvitations, activeTab]);

// Tab pills
const tabs = [
  { key: 'super_admins', label: 'Super Admins', count: superAdmins.length },
  { key: 'all_admins',   label: 'All Org Admins', count: admins.length },
  { key: 'pending',      label: 'Pending Invitations', count: pendingInvitations.length },
];

// Each tab shows its count in a badge
<button className={cn("px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors flex items-center gap-1.5",
  activeTab === tab.key ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"
)}>
  {tab.label}
  <span className={cn("text-xs rounded-full px-1.5 py-0.5",
    activeTab === tab.key ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-500"
  )}>{tab.count}</span>
</button>
```

### 6C — Filter Button (Admin Control)

Opens a filter popover with options:
- Role: All / Super Admin / Category Admin
- Status: All / Active / Suspended
- Organization: dropdown of all orgs

### 6D — Download Button (Admin Control)

```jsx
function downloadAdminsCSV() {
  const data = displayedAdmins;
  const headers = ['Name', 'Email', 'Organization', 'Role', 'Last Login', 'Status'];
  const rows = data.map(a => [a.name, a.email, a.orgName, a.role, a.lastLogin, a.status]);
  downloadCSV(rows, headers, `admins-${activeTab}-${Date.now()}.csv`);
}
```

### 6E — Row Action Buttons in Admin Table

Each admin row on hover reveals 3 action buttons on the right:

```jsx
// For ACTIVE admins:
// 1. Reset Password (key icon) → opens confirm dialog
// 2. Suspend (ban icon) → confirm → sets status to suspended
// 3. Delete (trash icon) → confirm with red destructive button

// For SUSPENDED admins:
// 1. Restore (undo icon) → confirm → sets status to active
// 2. Delete (trash icon)

// For PENDING INVITATIONS:
// 1. Resend (mail icon) → toast "Invitation resent"
// 2. Revoke (x icon) → confirm → removes from pending list

function AdminRowActions({ admin }) {
  if (admin.status === 'pending') {
    return (
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <ActionButton icon={<MailIcon size={14}/>} label="Resend invite"
          onClick={() => { toast.success(`Invite resent to ${admin.email}`); }} />
        <ActionButton icon={<XIcon size={14}/>} label="Revoke invite" variant="danger"
          onClick={() => confirmThenRevoke(admin.id)} />
      </div>
    );
  }
  if (admin.status === 'suspended') {
    return (
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <ActionButton icon={<UndoIcon size={14}/>} label="Restore access"
          onClick={() => confirmThenRestore(admin.id)} />
        <ActionButton icon={<TrashIcon size={14}/>} label="Delete admin" variant="danger"
          onClick={() => confirmThenDelete(admin.id)} />
      </div>
    );
  }
  return (
    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <ActionButton icon={<KeyIcon size={14}/>} label="Reset password"
        onClick={() => confirmPasswordReset(admin)} />
      <ActionButton icon={<BanIcon size={14}/>} label="Suspend admin"
        onClick={() => confirmThenSuspend(admin.id)} />
      <ActionButton icon={<TrashIcon size={14}/>} label="Delete admin" variant="danger"
        onClick={() => confirmThenDelete(admin.id)} />
    </div>
  );
}
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TASK 7 — Shared: Confirmation Dialog + Toast System
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Goal
Both Organizations and Admin Control need a reusable confirmation dialog and a toast notification system. These must be built once and shared.

### Confirmation Dialog

```jsx
// hooks/useConfirm.ts
// Returns a promise-based confirm() function

export function useConfirm() {
  const [state, setState] = useState(null);

  const confirm = (options) => new Promise((resolve) => {
    setState({ ...options, resolve });
  });

  const handleConfirm = () => { state.resolve(true); setState(null); };
  const handleCancel  = () => { state.resolve(false); setState(null); };

  const ConfirmDialog = state ? (
    <AlertDialog open>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{state.title}</AlertDialogTitle>
          <AlertDialogDescription>{state.description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm}
            className={state.variant === 'destructive' ? 'bg-red-600 hover:bg-red-700' : ''}>
            {state.confirmLabel || 'Confirm'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  ) : null;

  return { confirm, ConfirmDialog };
}
```

### Toast System

Use `sonner` (already in most Next.js + shadcn setups):

```jsx
// layout.tsx — add at root
import { Toaster } from 'sonner';
<Toaster position="bottom-right" richColors />

// Usage anywhere:
import { toast } from 'sonner';
toast.success('Organization suspended');
toast.error('Failed to sync — try again');
toast.info('Invitation sent to admin@telite.io');
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TASK 8 — State Management Architecture
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Goal
All interactive state (search query, org list, admin list, pending invitations, notifications, sync status) must be managed in a single Zustand store so that:
- Search in the top bar filters data on the currently active page
- Actions on one page reflect instantly everywhere (suspend org → count updates in sidebar badge)
- Sync state is shared between Dashboard sync strip and any sync status indicators

### Store Definition

```typescript
// store/adminConsoleStore.ts
import { create } from 'zustand';

interface AdminConsoleStore {
  // Search
  searchQuery: string;
  setSearchQuery: (q: string) => void;

  // Organizations
  organizations: Organization[];
  updateOrgStatus: (id: number, status: OrgStatus) => void;
  addOrganization: (org: Partial<Organization>) => void;

  // Admins
  admins: Admin[];
  pendingInvitations: Invitation[];
  updateAdminStatus: (id: number, status: AdminStatus) => void;
  addInvitation: (inv: Invitation) => void;
  revokeInvitation: (id: number) => void;

  // Notifications
  notifications: Notification[];
  markAllRead: () => void;
  unreadCount: number;

  // Sync
  isSyncing: boolean;
  lastSync: string;
  syncProgress: number;
  triggerSync: () => Promise<void>;

  // UI
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useAdminStore = create<AdminConsoleStore>((set, get) => ({
  // ... full implementation
}));
```

### Computed Selectors

```typescript
// Derived from store, used in components
export const useFilteredOrgs = (filter: OrgFilter, query: string) => {
  const orgs = useAdminStore(s => s.organizations);
  return useMemo(() => {
    let result = orgs;
    if (query.length >= 2) {
      result = result.filter(o =>
        o.name.toLowerCase().includes(query.toLowerCase()) ||
        o.domain.toLowerCase().includes(query.toLowerCase())
      );
    }
    if (filter !== 'all') {
      result = result.filter(o =>
        filter === 'inactive' ? o.status === 'INACTIVE' : o.type === filter.toUpperCase()
      );
    }
    return result;
  }, [orgs, filter, query]);
};
```

---

## 📋 EXECUTION ORDER

```
Task 1 → Layout scale fix           (30 min) — unblocks all visual work
Task 2 → Sidebar redesign + toggle  (45 min) — core UX change
Task 7 → Toast + Confirm system     (20 min) — needed by Tasks 5 & 6
Task 8 → Zustand store              (30 min) — needed by Tasks 3, 5, 6
Task 3 → Top bar search + notifs    (45 min)
Task 4 → Dashboard FAB + Sync       (30 min)
Task 5 → Organizations full fix     (60 min) — most changes
Task 6 → Admin Control full fix     (60 min) — most changes
```

---

## 🎨 DESIGN TOKENS (Apply Globally)

```css
/* Color system — clean minimal enterprise palette */
--color-primary:       #4648D4;
--color-primary-hover: #3730C4;
--color-primary-bg:    #EEF2FF;
--color-primary-text:  #4338CA;
--color-sidebar-bg:    #FFFFFF;
--color-topbar-bg:     #FFFFFF;
--color-page-bg:       #F9FAFB;
--color-border:        #E5E7EB;
--color-border-focus:  #4648D4;
--color-text-primary:  #111827;
--color-text-secondary:#6B7280;
--color-text-muted:    #9CA3AF;
--color-success:       #059669;
--color-warning:       #D97706;
--color-error:         #DC2626;

/* Typography */
--font-display: 'Inter', sans-serif;
--text-xs:   11px;
--text-sm:   13px;
--text-base: 14px;
--text-lg:   16px;
--text-xl:   18px;
--text-2xl:  22px;
--text-3xl:  28px;
```

---

## ✅ DEFINITION OF DONE

A task is complete when:
1. The feature works at `1280px` viewport without horizontal scroll
2. All buttons/interactions have visual feedback (hover, active, loading state)
3. Confirmation dialogs appear before destructive actions
4. Toast notifications confirm successful actions
5. No TypeScript errors (`tsc --noEmit` passes)
6. State updates are reflected immediately without page refresh

---
*Authored by: Prompt Engineer + Design Engineer + Full-Stack Engineer*
*Estimated total implementation time: ~5.5 hours*
*Target framework: Next.js 14 + Tailwind CSS + shadcn/ui + Zustand + Sonner*
