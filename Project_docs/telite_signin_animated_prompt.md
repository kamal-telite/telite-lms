# 🎯 MASTER PROMPT — Telite LMS Animated Sign-In Page
## Role: Design Engineer + Prompt Engineer | Stack: GSAP · Vanta.js · Typed.js · Vanilla Tilt · Three.js

---

## 🧠 ROLE & MISSION

You are a **senior motion design engineer and creative technologist** rebuilding the Telite LMS sign-in page as a cinematic, single-screen experience. You have deeply studied the original design (purple-to-blue gradient background, two-column layout: left — hero copy + role cards; right — sign-in modal).

**Core constraint:** The page must feel like a premium SaaS product. The sign-in modal is a floating, blurred-glass popup over an animated full-screen background. No extra elements. No icons (logo text only). No placeholders. Everything real.

---

## 🎨 AESTHETIC DIRECTION — "Weightless Glass"

**Concept:** The entire viewport is an animated living background. The sign-in modal floats above it as a frosted glass popup — separated from the world by backdrop-filter blur. The left hero section lives behind the blur, part of the animated scene.

**Visual Language:**
- **Background:** Full-screen Vanta.js NET animation — deep indigo (`#0d0b2e`) particles forming a constellation mesh. Mouse-interactive. This IS the background — the entire page bg.
- **Left hero:** Overlaid directly on the Vanta background, text in white. Part of the animated scene, not a separate panel. Has parallax depth on scroll/mouse.
- **Modal (right):** Frosted glass card — `backdrop-filter: blur(24px)`, semi-transparent white (`rgba(255,255,255,0.08)`), razor-thin `1px solid rgba(255,255,255,0.15)` border. Feels like it's floating.
- **Typography:** `Clash Display` (headline — massive, bold, tight tracking), `Cabinet Grotesk` (body, labels, inputs). Load via Fontshare.
- **Colour palette:** `#4648d4` primary indigo, `#6366f1` lighter accent, `#f98012` amber highlight, `#0d0b2e` deep navy bg, white text on dark, `rgba(255,255,255,0.06)` input backgrounds.
- **Motion signature:** Everything enters with weighted ease. Modal pops up from below with a spring bounce. Text stagers word-by-word. Input focus states have a subtle glow pulse.

---

## 📦 TECH STACK (All Free CDN — Exact Versions)

```html
<!-- GSAP Core + ScrollTrigger -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>

<!-- Three.js (Vanta dependency) -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script>

<!-- Vanta NET (animated constellation background) -->
<script src="https://cdn.jsdelivr.net/npm/vanta@latest/dist/vanta.net.min.js"></script>

<!-- Typed.js (typewriter cycling in the headline) -->
<script src="https://cdn.jsdelivr.net/npm/typed.js@2.1.0/dist/typed.umd.js"></script>

<!-- Vanilla Tilt (3D tilt on the glass modal) -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/vanilla-tilt/1.8.1/vanilla-tilt.min.js"></script>

<!-- Fonts: Clash Display + Cabinet Grotesk -->
<link href="https://api.fontshare.com/v2/css?f[]=clash-display@600,700&f[]=cabinet-grotesk@400,500,700&display=swap" rel="stylesheet"/>
```

**NOT used:** Lottie (no icons), Splitting.js (not needed for single-screen). Keep the stack lean.

---

## 🏗️ PAGE STRUCTURE — EXACTLY THIS, NOTHING MORE

```
FULL VIEWPORT
├── #vanta-bg          (fixed, full-screen, z-index: 0)
├── .page-wrap         (flex row, full viewport, z-index: 1)
│   ├── .hero-left     (50% width, overlaid on Vanta — NOT a separate bg)
│   │   ├── .logo-row  (text logo "TS" + "Telite Systems LMS" + tagline)
│   │   ├── .eyebrow   ("INTERNAL LEARNING PLATFORM" — spaced caps)
│   │   ├── .headline  (Clash Display, massive — Typed.js cycles)
│   │   ├── .sub-desc  (one sentence description)
│   │   └── .role-cards (3 cards: Super Admin / ATS Admin / Learner)
│   └── .modal-wrap    (50% width, flex center)
│       └── .glass-modal (THE SIGN-IN CARD — frosted glass popup)
│           ├── h2 "Sign in"
│           ├── .modal-sub (subtitle text)
│           ├── .field-group (Username input)
│           ├── .field-group (Password input)
│           ├── .btn-open-workspace (magnetic CTA)
│           ├── .quick-signin-section
│           │   ├── "QUICK SIGN-IN" label
│           │   └── 3 role rows (Super Admin / ATS Admin / Learner)
│           └── .create-account-link
```

**NOTHING ELSE. No footer. No navbar. No extra sections. No icons anywhere.**

---

## 🌌 BACKGROUND ANIMATION SPEC

```javascript
// VANTA NET — full screen, deep navy, white-ish particles
VANTA.NET({
  el: "#vanta-bg",
  mouseControls: true,
  touchControls: true,
  gyroControls: false,
  minHeight: 200,
  minWidth: 200,
  scale: 1.0,
  scaleMobile: 1.0,
  color: 0x4648d4,          // indigo particle lines
  backgroundColor: 0x0d0b2e, // deep navy
  points: 14.0,
  maxDistance: 26.0,
  spacing: 18.0,
  showDots: true
})
```

**Key point:** The left hero text sits directly on this background. No separate panel. The Vanta animation IS the full page.

---

## ✍️ TYPEWRITER SPEC (Typed.js)

The headline reads: **"One workspace for [TYPED]."**

```javascript
new Typed('#typed-word', {
  strings: [
    'categories.',
    'learners.',
    'PAL tracking.',
    'Moodle launch.',
    'your institution.'
  ],
  typeSpeed: 65,
  backSpeed: 35,
  backDelay: 2200,
  loop: true,
  cursorChar: '_',
  smartBackspace: true
})
```

Headline structure:
```html
<h1 class="headline">
  One workspace for<br>
  <span id="typed-word"></span>
</h1>
```

Typed text inherits the headline size. Cursor `_` stays amber `#f98012`.

---

## 💎 GLASS MODAL SPEC

### Visual
```css
.glass-modal {
  background: rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 28px;
  padding: 44px 40px;
  width: 420px;
  box-shadow:
    0 32px 80px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
```

### Entrance animation (GSAP — modal pops up from below on page load)
```javascript
gsap.from(".glass-modal", {
  y: 80,
  opacity: 0,
  scale: 0.94,
  duration: 1.0,
  delay: 0.6,
  ease: "back.out(1.6)"
})
```

### 3D Tilt (Vanilla Tilt)
```javascript
VanillaTilt.init(document.querySelector(".glass-modal"), {
  max: 6,
  speed: 600,
  glare: true,
  "max-glare": 0.08,
  scale: 1.01,
  perspective: 1200,
  "full-page-listening": false
})
```

### Input focus glow
```css
.field-input:focus {
  outline: none;
  border-color: rgba(70, 72, 212, 0.6);
  box-shadow: 0 0 0 3px rgba(70, 72, 212, 0.15),
              0 0 20px rgba(70, 72, 212, 0.08);
  background: rgba(255, 255, 255, 0.1);
}
```

---

## 🧲 MAGNETIC CTA BUTTON — "Open workspace"

```javascript
// Magnetic push/pull on mousemove
const btn = document.querySelector('.btn-open-workspace');
btn.addEventListener('mousemove', (e) => {
  const rect = btn.getBoundingClientRect();
  const x = (e.clientX - rect.left - rect.width / 2) * 0.4;
  const y = (e.clientY - rect.top - rect.height / 2) * 0.4;
  gsap.to(btn, { x, y, duration: 0.3, ease: "power2.out" });
});
btn.addEventListener('mouseleave', () => {
  gsap.to(btn, { x: 0, y: 0, duration: 0.6, ease: "elastic.out(1, 0.4)" });
});
```

Button style:
```css
.btn-open-workspace {
  width: 100%;
  background: linear-gradient(135deg, #4648d4, #6366f1);
  color: #fff;
  font-family: 'Cabinet Grotesk', sans-serif;
  font-size: 15px;
  font-weight: 700;
  padding: 16px 24px;
  border: none;
  border-radius: 14px;
  cursor: none;
  position: relative;
  overflow: hidden;
  letter-spacing: 0.01em;
  /* Shimmer on hover via ::after */
}
.btn-open-workspace::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.2) 50%, transparent 70%);
  transform: translateX(-150%);
  transition: transform 0.6s ease;
}
.btn-open-workspace:hover::after { transform: translateX(150%); }
.btn-open-workspace:hover {
  box-shadow: 0 12px 32px rgba(70, 72, 212, 0.6);
}
```

---

## 📐 HERO LEFT — PARALLAX SPEC

The entire left column moves subtly opposite to the mouse — creating depth between the background particles and the foreground text.

```javascript
document.addEventListener('mousemove', (e) => {
  const xPct = (e.clientX / window.innerWidth - 0.5);
  const yPct = (e.clientY / window.innerHeight - 0.5);

  gsap.to(".hero-left", {
    x: xPct * -18,
    y: yPct * -12,
    duration: 1.2,
    ease: "power2.out"
  });
  gsap.to(".logo-row", {
    x: xPct * -10,
    y: yPct * -8,
    duration: 1.4,
    ease: "power2.out"
  });
});
```

Different parallax speeds per layer creates a real sense of 3D depth against the Vanta particles.

---

## 🎬 PAGE LOAD SEQUENCE (GSAP Timeline)

```javascript
const tl = gsap.timeline({ delay: 0.2 });

tl
  // 1. Logo fades in from top
  .from(".logo-row", { y: -30, opacity: 0, duration: 0.7, ease: "power3.out" })

  // 2. Eyebrow label
  .from(".eyebrow", { y: 20, opacity: 0, duration: 0.5, ease: "power2.out" }, "-=0.3")

  // 3. Headline words stagger (each line)
  .from(".headline", { y: 50, opacity: 0, duration: 0.9, ease: "power3.out" }, "-=0.2")

  // 4. Sub description
  .from(".sub-desc", { y: 20, opacity: 0, duration: 0.6, ease: "power2.out" }, "-=0.5")

  // 5. Role cards stagger up
  .from(".role-card", { y: 30, opacity: 0, stagger: 0.12, duration: 0.6, ease: "back.out(1.3)" }, "-=0.3")

  // 6. Modal springs in from below
  .from(".glass-modal", { y: 80, opacity: 0, scale: 0.94, duration: 1.0, ease: "back.out(1.6)" }, "-=0.8")

  // 7. Modal children stagger
  .from(".modal-child", { y: 16, opacity: 0, stagger: 0.08, duration: 0.5, ease: "power2.out" }, "-=0.5")
```

---

## 🃏 ROLE CARDS SPEC (left side, below headline)

Three frosted mini-cards stacked vertically. Each clickable — clicking auto-fills the username field.

```css
.role-card {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 18px 22px;
  cursor: none;
  transition: background 0.3s, border-color 0.3s, transform 0.2s;
}
.role-card:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(70, 72, 212, 0.4);
  transform: translateX(6px);
}
.role-card-title { font-weight: 700; font-size: 14px; color: #fff; margin-bottom: 4px; }
.role-card-desc  { font-size: 12px; color: rgba(255,255,255,0.45); line-height: 1.5; }
```

Role cards data (real content, no placeholders):
```javascript
const roles = [
  {
    title: "Super Admin",
    desc: "Cross-category control, audit, admin delegation, and enrollment approvals."
  },
  {
    title: "ATS Admin",
    desc: "Course operations, learner management, PAL tracking, and task assignment."
  },
  {
    title: "Learner",
    desc: "Progress view, Moodle launch, tasks, notifications, and personal PAL insight."
  }
];
```

---

## ⚡ QUICK SIGN-IN ROWS SPEC (inside modal)

Three rows inside the modal, below the CTA button. Each row auto-fills credentials on click.

```html
<!-- QUICK SIGN-IN header -->
<div class="qs-label">QUICK SIGN-IN</div>

<!-- Row -->
<div class="qs-row" onclick="fillCreds('superadmin', 'Super@1234')">
  <div>
    <div class="qs-role">Super Admin</div>
    <div class="qs-username">superadmin</div>
  </div>
  <div class="qs-password">Super@1234</div>
</div>

<div class="qs-row" onclick="fillCreds('anika', 'Admin@1234')">
  <div>
    <div class="qs-role">ATS Admin</div>
    <div class="qs-username">anika</div>
  </div>
  <div class="qs-password">Admin@1234</div>
</div>

<div class="qs-row" onclick="fillCreds('rahul', 'Learner@1234')">
  <div>
    <div class="qs-role">Learner</div>
    <div class="qs-username">rahul</div>
  </div>
  <div class="qs-password">Learner@1234</div>
</div>
```

```javascript
function fillCreds(user, pass) {
  const uInput = document.getElementById('username');
  const pInput = document.getElementById('password');

  // Animate fill with GSAP flash
  gsap.to([uInput, pInput], {
    borderColor: "rgba(70,72,212,0.6)",
    duration: 0.2,
    yoyo: true, repeat: 1
  });

  uInput.value = user;
  pInput.value = pass;
}
```

---

## 🖱️ CUSTOM CURSOR

```css
.cursor       { width: 36px; height: 36px; border: 1.5px solid rgba(70,72,212,0.7); border-radius: 50%; position: fixed; pointer-events: none; z-index: 9999; transform: translate(-50%,-50%); transition: width .3s, height .3s, background .3s; mix-blend-mode: screen; }
.cursor-dot   { width: 5px;  height: 5px;  background: #4648d4; border-radius: 50%; position: fixed; pointer-events: none; z-index: 9999; transform: translate(-50%,-50%); }
```

```javascript
document.addEventListener('mousemove', (e) => {
  gsap.to(".cursor",     { x: e.clientX, y: e.clientY, duration: 0.6, ease: "power2.out" });
  gsap.to(".cursor-dot", { x: e.clientX, y: e.clientY, duration: 0.1 });
});
// Expand on interactive elements
document.querySelectorAll('button, .role-card, .qs-row, a, input').forEach(el => {
  el.addEventListener('mouseenter', () => gsap.to(".cursor", { scale: 1.8, duration: 0.3 }));
  el.addEventListener('mouseleave', () => gsap.to(".cursor", { scale: 1.0, duration: 0.3 }));
});
```

---

## 📋 COMPLETE CONTENT (No Placeholders)

### Logo Row
```
[TS]  Telite Systems LMS
      Role-aware learning operations for ATS
```
Logo is pure CSS — `TS` text in a rounded indigo square. No SVG icon, no image.

### Eyebrow
```
INTERNAL LEARNING PLATFORM
```
Letter-spaced caps, small, indigo-coloured.

### Headline (Typed cycles through these)
```
One workspace for categories.
One workspace for learners.
One workspace for PAL tracking.
One workspace for Moodle launch.
One workspace for your institution.
```

### Sub-description
```
Sign in as Super Admin, ATS Admin, or a learner to access the real dashboards wired to the Telite backend.
```

### Modal title
```
Sign in
```

### Modal subtitle
```
Use the seeded Telite credentials to open the live dashboards.
```

### Field labels
```
Username
Password
```

### CTA
```
Open workspace
```

### Quick Sign-In
```
QUICK SIGN-IN

Super Admin     superadmin     Super@1234
ATS Admin       anika          Admin@1234
Learner         rahul          Learner@1234
```

### Footer link
```
Don't have an account?  Create Account
```

---

## 🔑 CRITICAL IMPLEMENTATION RULES

1. **body { cursor: none }** — custom cursor replaces system cursor everywhere
2. **#vanta-bg position: fixed, inset: 0, z-index: 0** — particles always full-screen behind everything
3. **Glass modal z-index: 10** — always above Vanta
4. **NO icons anywhere** — logo is text "TS" styled in CSS only
5. **NO placeholder text in inputs** — label stays above the field (floating label or static label)
6. **VanillaTilt.init() after fonts load** — wrap in `document.fonts.ready.then()`
7. **Typed.js starts AFTER GSAP headline entrance** — add it in the GSAP timeline `onComplete`
8. **Input type="password"** has `autocomplete="current-password"` — browser fills correctly
9. **Quick sign-in rows have a hover slide-right** on `transform: translateX(4px)` transition
10. **Modal backdrop-filter** requires the Vanta background to have real content — it must be behind, not beside, the modal

---

## 🎬 ANIMATION TIMING REFERENCE

| Element              | Delay  | Duration | Ease                 |
|----------------------|--------|----------|----------------------|
| Logo row             | 0.2s   | 0.7s     | power3.out           |
| Eyebrow              | 0.5s   | 0.5s     | power2.out           |
| Headline             | 0.7s   | 0.9s     | power3.out           |
| Sub-description      | 1.0s   | 0.6s     | power2.out           |
| Role cards (stagger) | 1.1s   | 0.6s     | back.out(1.3)        |
| Glass modal          | 0.6s   | 1.0s     | back.out(1.6)        |
| Modal field stagger  | 1.2s   | 0.5s     | power2.out           |
| Typed.js starts      | after headline entrance complete |  |           |

---

## 📋 FINAL DELIVERABLE CHECKLIST

- [ ] Vanta NET full-screen fixed background (deep navy + indigo particles)
- [ ] Left hero: logo (CSS text "TS"), eyebrow, typed headline, sub-desc, 3 role cards
- [ ] Right: frosted glass modal with blur, tilt, spring entrance
- [ ] Username + Password fields with glow-on-focus, no placeholder text
- [ ] "Open workspace" magnetic button with shimmer and shadow on hover
- [ ] Quick sign-in rows — clickable, auto-fill credentials with GSAP flash
- [ ] "Don't have an account? Create Account" link
- [ ] Custom dual-layer cursor (ring + dot)
- [ ] Parallax on hero left (mouse-driven depth)
- [ ] GSAP load timeline — staggered entrance of ALL elements
- [ ] Typed.js cycles through 5 strings in the headline
- [ ] 3D tilt on the glass modal (Vanilla Tilt, gentle)
- [ ] Reduced-motion fallback — skip animations if prefers-reduced-motion
- [ ] All content real — zero placeholders, zero lorem ipsum

---
*Generated by: Design Engineer + Prompt Engineer*
*Target output: Single-file HTML — production-grade, cinematic, no extras*
