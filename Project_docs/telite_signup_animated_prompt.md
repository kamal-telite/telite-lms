You are a senior design engineer and prompt engineer. Build a fully animated, 
production-grade multi-step signup page for "Telite LMS" as a single self-contained 
HTML file using GSAP, Vanta.js (NET), and Three.js. No frameworks, no build tools, 
no external assets. All libraries via CDN only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPOGRAPHY & FONTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Load via Google Fonts: DM Sans (300,400,500) + Syne (400,600,700)
- Body: DM Sans
- Headings, logo, captcha: Syne
- No system fonts, no Inter, no Roboto

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BACKGROUND — VANTA.JS NET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Full-screen fixed Vanta NET animation behind everything
- color: 0x6040d0, backgroundColor: 0x050510
- points: 8, maxDistance: 18, spacing: 15, showDots: false
- mouseControls and touchControls both enabled
- Load order: three.js r128 → gsap 3.12.2 → vanta.net (jsdelivr)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CARD — GLASSMORPHISM, WIDE, CENTERED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Single centered card: width min(680px, calc(100vw - 48px))
- padding: 44px 56px
- background: rgba(10,8,20,0.72)
- backdrop-filter: blur(28px) saturate(180%)
- border: 1px solid rgba(255,255,255,0.15)
- border-radius: 24px
- box-shadow: 0 32px 80px rgba(0,0,0,0.6)
- Two radial gradient overlays as ::before (purple top-left, teal bottom-right at low opacity)
- Mouse-tracking card shine: radial highlight follows cursor using CSS custom properties 
  --mx and --my, opacity 0 → 1 on hover
- card-wrap: perspective 1000px, same width as card, margin 0 auto
- page: position fixed, inset 0, flex, align+justify center

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOGO — TEXT ONLY, NO ICON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Text wordmark only: "Telite LMS" in Syne 700, font-size 20px
- Apply CSS gradient text: background linear-gradient(110deg, #fff 30%, 
  rgba(139,124,248,0.9) 70%, #5de8c5), use -webkit-background-clip: text
- Below it: "New account registration" label in DM Sans 11px, 
  color rgba(122,122,138,0.8), uppercase, letter-spacing 0.06em
- NO square icon, NO logo mark, NO TS badge, NO emoji anywhere
- "Sign in instead" ghost pill button floated right with margin-left: auto

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CUSTOM CURSOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Hide default cursor: cursor: none on body
- Small dot (10px) fixed, background var(--accent), mix-blend-mode: screen
- Outer ring (36px) fixed, border 1px solid rgba(139,124,248,0.3), 
  follows with 80ms setTimeout delay
- On hover over interactive elements: dot scales to 2.5x, color shifts to 
  rgba(139,124,248,0.4)
- Attach hover listeners to: button, input, select, .card-option

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3D TILT EFFECT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- On mousemove: calculate dx/dy relative to card center
- gsap.to(mainCard): rotationX = dy * -10, rotationY = dx * 10
- transformPerspective: 900, duration 0.6, ease power2.out
- On mouseleave: gsap elastic reset rotationX/Y to 0, 
  duration 0.8, ease elastic.out(1, 0.4)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAGNETIC BUTTONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Apply class magnetic-wrap to: "Sign in instead" btn + "Submit Registration" btn
- On mousemove: gsap.to(btn) x = dx * 0.25, y = dy * 0.25, duration 0.3, power2.out
- On mouseleave: gsap elastic spring back to x:0, y:0, 
  duration 0.5, elastic.out(1, 0.4)
- Call initMagnetic() after every step transition and form build

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPEWRITER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- On Step 1 load: type "organization type" into a .type-target span
  character by character at 55ms interval
- Blinking cursor: adjacent span, width 2px, height 1em, 
  background var(--accent), CSS blink animation (step-end, 1s infinite)
- Re-trigger typewriter when user navigates back to Step 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GSAP ENTRANCE ANIMATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- #main-card: from y:60, opacity:0, scale:0.95 → duration 1s, expo.out, delay 0.1
- .logo-row: from y:20, opacity:0 → duration 0.8, power3.out, delay 0.4
- .stepper: from y:16, opacity:0 → duration 0.8, power3.out, delay 0.55
- #step1: from y:12, opacity:0 → duration 0.7, power3.out, delay 0.65
- Step transitions: gsap.from the incoming step, y:10, opacity:0, 
  duration 0.35, power2.out
- Form fields on build: gsap.from(ff.children), stagger 0.05, y:8, opacity:0
- Role cards on render: gsap.from(grid.children), stagger 0.06, y:10, opacity:0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP FLOW — 3 STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1 — Choose Organization Type:
  - Two clickable cards: "College" and "Company"
  - Each card: opt-title + opt-sub description
  - On click: mark selected, populate Step 2 roles, goStep(2) after 220ms delay

Step 2 — Select Role:
  - Back arrow button (←) returns to Step 1
  - Heading: "Select your role — College" or "Select your role — Company"
  - College roles: Student, Teacher, College Admin, College Super Admin
  - Company roles: Intern, Employee, Project Admin, Company Admin
  - Each has a subtitle description
  - On click: buildForm(role), goStep(3)

Step 3 — Registration Form:
  - Back arrow returns to Step 2
  - Heading: "Register as {Role}"
  - Breadcrumb: "{Org} → {Role}" as pill tags (text only, no emoji)
    Active tag: accent border + accent color + accent background tint
  - Dynamic field grid (2 columns): fields vary by role
  - All roles get: Full Name, Email, Org Name (select dropdown), ID field,
    Password, Confirm Password
  - Student adds: Program, Branch
  - Teacher adds: Department, Specialization
  - Intern/Employee adds: Department/Team, Phone Number
  - Admin roles add: Designation, Phone Number
  - Security Check: math captcha rendered as styled gradient box 
    "A + B = ?" beside number input
  - Actions row: Back (ghost) | Reload (ghost) | Submit Registration (gradient, magnetic)
  - Wrong captcha: GSAP shake animation on card (x: -8, repeat 5, yoyo)
  - Correct captcha: GSAP scale pulse (1.02, yoyo)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEPPER INDICATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 3 circles connected by 1px lines, centered
- Inactive: border 1px rgba(255,255,255,0.1), text muted
- Active: background var(--accent) #8b7cf8, glow box-shadow, scale 1.1, 
  transition cubic-bezier(0.34,1.56,0.64,1)
- Done: background rgba(93,232,197,0.2), border var(--accent2), 
  show ✓ checkmark, hide number

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORM INPUTS STYLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- background: rgba(255,255,255,0.04)
- border: 1px solid rgba(255,255,255,0.1)
- border-radius: 8px, padding 10px 13px
- color: #f0f0f0, font DM Sans 13px
- On focus: border rgba(139,124,248,0.6), box-shadow 0 0 0 3px rgba(139,124,248,0.1)
- Select: custom dropdown SVG arrow, background #0e0c1f for options
- Labels: 11px, uppercase, letter-spacing 0.03em, color muted
- Form section: scrollable (max-height calc(100vh - 300px)), 
  thin 3px scrollbar, transparent track

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUTTONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Ghost buttons (Back, Reload): border 1px input-border, transparent bg, 
  border-radius 20px, color muted → full white on hover
- Primary (Submit): linear-gradient(135deg, #7c6ff7, #5de8c5), 
  border-radius 20px, margin-left auto
  On hover: translateY(-2px) + box-shadow 0 8px 30px rgba(139,124,248,0.5)
  ::after overlay (rgba white) fades in on hover for shimmer
  On active: scale(0.97)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COLOR TOKENS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
--accent: #8b7cf8 (purple)
--accent2: #5de8c5 (teal)
--text: #f0f0f0
--text-dim: #7a7a8a
--card-bg: rgba(10,8,20,0.72)
--input-bg: rgba(255,255,255,0.04)
--input-border: rgba(255,255,255,0.1)
--glass-border: rgba(255,255,255,0.15)
--glass-hover: rgba(255,255,255,0.12)
body background: #050510
Captcha box: gradient rgba(139,124,248,0.3) → rgba(93,232,197,0.2)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION CARDS (Org + Role cards)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- padding 18px 16px, border-radius 14px, border input-border, bg input-bg
- ::before pseudo: gradient rgba(139,124,248,0.12)→rgba(93,232,197,0.06), 
  opacity 0 → 1 on hover
- Hover: border rgba(255,255,255,0.2), translateY(-2px), shadow
- Selected: border var(--accent), bg rgba(139,124,248,0.1)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONSTRAINTS — STRICTLY FOLLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Single HTML file, no external CSS/JS files
- CDN only: cdnjs.cloudflare.com + cdn.jsdelivr.net + fonts.googleapis.com
- overflow: hidden on html and body (no page scroll, card scrolls internally)
- cursor: none on body — custom cursor only
- No emoji anywhere in the UI
- No icons (no Lucide, no Font Awesome, no SVG icon sets)
- No placeholder text in any input field
- Logo is pure text only — no mark, no badge, no symbol
- All animations run on load — no user action required to trigger entrance
- The card must be perfectly centered both horizontally and vertically at all times
