# 🎯 MASTER PROMPT — Telite LMS Animated Landing Page Upgrade
## For: Design Engineer + Prompt Engineer | Stack: GSAP · Vanta.js · Spline · Lottie · Three.js

---

## 🧠 ROLE & CONTEXT

You are a **senior creative technologist and motion design engineer** building a world-class animated SaaS landing page for **Telite LMS** — a multi-tenant learning platform for colleges, companies, and training institutes. You have studied the existing admin console design system (glassmorphism, indigo/violet primary palette `#4648d4`, Space Grotesk + Inter typography, neumorphic surfaces) and must reflect that identity on the public-facing marketing site while dramatically elevating it with motion.

The current landing page is functional but static. Your mission: rebuild it as a **cinematic, interactive experience** that feels as premium as Linear, Vercel, or Stripe's marketing sites — but with an **educational-tech identity**.

---

## 🎨 AESTHETIC DIRECTION — "Deep Learning Cosmos"

**Concept:** The universe of knowledge — dark cosmic backgrounds in hero sections fading to clean light surfaces for feature/pricing sections. Stars, neural networks, data flowing through space. Not cold/corporate — warm, intelligent, human.

**Visual Language:**
- **Hero:** Deep navy-to-indigo gradient (`#07006c` → `#4648d4` → `#1e1b4b`) with animated particle constellations (Vanta.js `NET`)
- **Sections:** White/`#f8f9ff` clean surfaces with glassmorphic floating cards
- **Accent:** Electric indigo `#4648d4`, violet `#6063ee`, warm amber `#f98012` (Moodle accent)
- **Typography:** `Clash Display` (headings — bold, geometric), `Cabinet Grotesk` (subheadings), `Inter` (body). Load via Fontshare CDN.
- **Motion Signature:** Everything enters with a slow, weighted ease. Nothing pops instantly. Gravity is felt.

---

## 📦 TECH STACK (All Free CDN)

```html
<!-- GSAP + ScrollTrigger + SplitText -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>

<!-- Three.js (Vanta dependency) -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script>

<!-- Vanta.js NET effect for hero -->
<script src="https://cdn.jsdelivr.net/npm/vanta@latest/dist/vanta.net.min.js"></script>

<!-- Lottie Web for micro-animations -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>

<!-- Splitting.js for char-level animations -->
<script src="https://unpkg.com/splitting/dist/splitting.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/splitting/dist/splitting.css">

<!-- Spline Runtime (3D scene embed) -->
<script type="module" src="https://unpkg.com/@splinetool/viewer@1.0.49/build/spline-viewer.js"></script>

<!-- Typed.js for typewriter -->
<script src="https://cdn.jsdelivr.net/npm/typed.js@2.1.0/dist/typed.umd.js"></script>

<!-- Vanilla Tilt for 3D card tilt -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/vanilla-tilt/1.8.1/vanilla-tilt.min.js"></script>
```

---

## 🏗️ SECTION-BY-SECTION ANIMATION BLUEPRINT

### 1. 🌌 NAVBAR
```
DESIGN:
- Transparent over hero, transitions to frosted glass (backdrop-blur-xl + bg-white/5 → bg-white/80) on scroll
- Logo: "Telite LMS" in Clash Display bold, indigo
- Links: Magnetic hover effect — cursor proximity warps the text 4px toward cursor using mousemove math
- CTA: "Get started free" — gradient border button, shimmer sweep on hover

GSAP:
gsap.from("nav", { y: -60, opacity: 0, duration: 1, ease: "power3.out" })

MAGNETIC BUTTON JS:
document.querySelectorAll('.magnetic').forEach(btn => {
  btn.addEventListener('mousemove', (e) => {
    const rect = btn.getBoundingClientRect();
    const x = (e.clientX - rect.left - rect.width/2) * 0.3;
    const y = (e.clientY - rect.top - rect.height/2) * 0.3;
    gsap.to(btn, { x, y, duration: 0.3, ease: "power2.out" });
  });
  btn.addEventListener('mouseleave', () => {
    gsap.to(btn, { x: 0, y: 0, duration: 0.5, ease: "elastic.out(1,0.4)" });
  });
});
```

---

### 2. 🚀 HERO SECTION — "One platform to manage learning"
```
LAYOUT:
- Full viewport height, dark cosmic background
- Left: headline stacks, subtext, CTAs
- Right: Spline 3D scene OR Vanta NET particle cloud with floating glassmorphic dashboard preview

VANTA.JS HERO BACKGROUND:
VANTA.NET({
  el: "#hero-bg",
  mouseControls: true,
  touchControls: true,
  gyroControls: false,
  minHeight: 200.00,
  minWidth: 200.00,
  scale: 1.00,
  scaleMobile: 1.00,
  color: 0x4648d4,       // primary indigo
  backgroundColor: 0x07006c, // deep navy
  points: 12.00,
  maxDistance: 22.00,
  spacing: 18.00
})

TYPEWRITER (Typed.js):
new Typed('#hero-typed', {
  strings: [
    'learning.',
    'users.',
    'analytics.',
    'content delivery.',
    'your institution.'
  ],
  typeSpeed: 60,
  backSpeed: 30,
  backDelay: 2000,
  loop: true,
  cursorChar: '_'
})
// Headline reads: "One platform to manage [TYPED TEXT]"

GSAP HERO ENTRANCE (staggered):
const heroTL = gsap.timeline({ delay: 0.3 });
heroTL
  .from(".hero-eyebrow", { opacity: 0, y: 20, duration: 0.6, ease: "power2.out" })
  .from(".hero-headline .word", { opacity: 0, y: 40, stagger: 0.08, duration: 0.8, ease: "power3.out" }, "-=0.3")
  .from(".hero-sub", { opacity: 0, y: 20, duration: 0.6 }, "-=0.4")
  .from(".hero-ctas", { opacity: 0, y: 20, duration: 0.5 }, "-=0.3")
  .from(".hero-badges", { opacity: 0, scale: 0.8, stagger: 0.1, duration: 0.4 }, "-=0.2")

FLOATING DASHBOARD MOCK:
- Glassmorphic card with real data (6 orgs, 17 courses, 81% score like screenshot)
- CSS: animation: float 6s ease-in-out infinite (translateY -12px loop)
- Vanilla Tilt on the card: data-tilt data-tilt-max="8" data-tilt-glare data-tilt-max-glare="0.2"

PARALLAX:
gsap.to(".hero-card", {
  y: -80,
  scrollTrigger: { trigger: "#hero", start: "top top", end: "bottom top", scrub: 1.5 }
})
gsap.to(".hero-particles", {
  y: -120, opacity: 0,
  scrollTrigger: { trigger: "#hero", start: "top top", end: "bottom top", scrub: 1 }
})
```

---

### 3. ✨ FEATURES SECTION — "Built for modern learning operations"
```
LAYOUT:
- Light `#f8f9ff` background — feels like surfacing from the cosmos
- 6-card bento grid with icons and descriptions
- Each card: glassmorphic, hover lifts with Vanilla Tilt

SCROLL REVEAL (GSAP ScrollTrigger):
gsap.from(".feature-card", {
  opacity: 0,
  y: 60,
  stagger: 0.12,
  duration: 0.8,
  ease: "power3.out",
  scrollTrigger: {
    trigger: ".features-grid",
    start: "top 80%",
    toggleActions: "play none none reverse"
  }
})

VANILLA TILT ON CARDS:
VanillaTilt.init(document.querySelectorAll(".feature-card"), {
  max: 12,
  speed: 400,
  glare: true,
  "max-glare": 0.15,
  scale: 1.03
})

LOTTIE ICONS:
// Each feature card has a Lottie animation instead of static icon
// Animations play on card hover using lottie.play() / lottie.stop()
// Source: LottieFiles free library — analytics, sync, users, shield, etc.
const anim = lottie.loadAnimation({
  container: document.getElementById('lottie-analytics'),
  renderer: 'svg',
  loop: false,
  autoplay: false,
  path: 'https://assets9.lottiefiles.com/packages/lf20_analytics.json'
});
card.addEventListener('mouseenter', () => anim.play());
card.addEventListener('mouseleave', () => anim.stop());

SECTION HEADER:
// Splitting.js char-level stagger on section title
Splitting();
gsap.from(".features-title .char", {
  opacity: 0, y: "100%", rotateX: -90,
  stagger: 0.025, duration: 0.6, ease: "back.out(1.5)",
  scrollTrigger: { trigger: ".features-title", start: "top 85%" }
})
```

---

### 4. 🎯 SOLUTIONS SECTION — "Built for your context"
```
LAYOUT:
- Two-column tabs: "For colleges" / "For companies"
- Left: animated checklist
- Right: Spline 3D scene (floating abstract shape representing academic vs corporate)

TAB SWITCHING: GSAP crossfade
gsap.to(".panel-college", { opacity: 0, x: -20, duration: 0.3 })
gsap.from(".panel-company", { opacity: 0, x: 20, duration: 0.4 })

CHECKLIST ITEMS: stagger reveal on tab switch
gsap.from(".check-item", {
  opacity: 0, x: -30, stagger: 0.1, duration: 0.5, ease: "power2.out"
})

SPLINE EMBED:
<spline-viewer 
  url="https://prod.spline.design/6Wq1Q7YoRtOEQHwR/scene.splinecode"
  style="width: 100%; height: 500px; border-radius: 24px;"
/>
// Use any abstract geometric Spline scene from spline.design community
// Alt: Use Vanta.js GLOBE or DOTS for visual interest without Spline

PARALLAX DEPTH on right column:
gsap.to(".solutions-visual", {
  y: -40,
  scrollTrigger: { trigger: "#solutions", scrub: 1.2 }
})
```

---

### 5. 📋 HOW IT WORKS — "Up and running in three steps"
```
LAYOUT:
- Horizontal scroll on mobile, vertical timeline on desktop
- 3 numbered steps with connection line animating between them

STEP LINE DRAW ANIMATION:
gsap.from(".step-connector", {
  scaleX: 0, transformOrigin: "left center",
  duration: 1.2, ease: "power2.inOut",
  scrollTrigger: { trigger: ".steps-row", start: "top 70%" }
})

STEP CARD ENTRANCE:
gsap.from(".step-card", {
  opacity: 0, scale: 0.85, y: 30,
  stagger: 0.2, duration: 0.7, ease: "back.out(1.3)",
  scrollTrigger: { trigger: ".steps-row", start: "top 75%" }
})

NUMBER COUNT-UP:
// Use GSAP counter for step numbers or any metric
gsap.from({val: 0}, {
  val: 3, duration: 1.5, ease: "power2.out",
  onUpdate: function() { el.textContent = Math.round(this.targets()[0].val) }
})
```

---

### 6. 💬 TESTIMONIALS — "Trusted by learning teams"
```
LAYOUT:
- Horizontal marquee/ticker (infinite scroll loop, CSS only)
- Cards with avatar, quote, star rating, company name
- On hover: marquee pauses, card scales up with shadow

MARQUEE CSS:
@keyframes marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
.marquee-track { animation: marquee 30s linear infinite; }
.marquee-track:hover { animation-play-state: paused; }

CARDS: Vanilla Tilt with gentle max=6
GSAP entry: fade in section title with SplitText char stagger
```

---

### 7. 💰 PRICING — "Simple, transparent pricing"
```
LAYOUT:
- 3 column cards (Starter/Pro/Enterprise)
- Pro card: elevated, glowing border, "Most Popular" badge
- Pricing toggle: Monthly/Annual (GSAP number flip animation)

PRO CARD GLOW:
.pricing-pro {
  box-shadow: 0 0 40px rgba(70, 72, 212, 0.3), 0 0 80px rgba(70, 72, 212, 0.1);
  border: 1px solid rgba(70, 72, 212, 0.4);
  animation: pulse-glow 3s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 40px rgba(70,72,212,0.3); }
  50% { box-shadow: 0 0 60px rgba(70,72,212,0.5); }
}

PRICE FLIP ANIMATION (toggle):
gsap.to(".price-number", {
  scrambleText: { text: "2,499", chars: "0123456789" },
  duration: 0.8
})

SCROLL REVEAL:
gsap.from(".pricing-card", {
  opacity: 0, y: 80, scale: 0.9, stagger: 0.15,
  scrollTrigger: { trigger: ".pricing-grid", start: "top 75%" }
})

VANILLA TILT on all cards: max=8, glare=true, max-glare=0.1
```

---

### 8. 🌐 CTA BANNER — "Ready to modernise?"
```
LAYOUT:
- Full-width dark section, Vanta WAVES background
- Headline with GSAP text scramble or typewriter on scroll enter
- Two magnetic CTA buttons with ripple click effect

VANTA WAVES:
VANTA.WAVES({
  el: "#cta-section",
  mouseControls: true,
  color: 0x4648d4,
  waveHeight: 20,
  shininess: 50,
  waveSpeed: 1
})

HEADLINE: GSAP SplitText word-by-word reveal
BUTTONS: Magnetic + ripple CSS on click
```

---

### 9. 🦶 FOOTER
```
- Dark `#1e1b4b` (matches admin sidebar), clean columns
- Logo animates in with GSAP scale from 0.7
- Links: underline draw on hover (CSS clip-path animation)
- Social icons: rotate 360deg on hover
```

---

## 🔧 GLOBAL ANIMATION RULES

```javascript
// 1. SMOOTH SCROLL
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.defaults({ markers: false });

// 2. CUSTOM CURSOR (optional, high-impact)
const cursor = document.querySelector('.cursor');
const cursorDot = document.querySelector('.cursor-dot');
document.addEventListener('mousemove', (e) => {
  gsap.to(cursor, { x: e.clientX, y: e.clientY, duration: 0.6, ease: "power2.out" });
  gsap.to(cursorDot, { x: e.clientX, y: e.clientY, duration: 0.1 });
});
// Cursor expands on hovering buttons/links

// 3. PAGE LOAD SEQUENCE
const loadTL = gsap.timeline();
loadTL
  .to(".loader-bar", { scaleX: 1, duration: 1, ease: "power2.inOut" })
  .to(".loader", { opacity: 0, duration: 0.4 })
  .set(".loader", { display: "none" })
  .add(heroEntrance);

// 4. SCROLL PROGRESS INDICATOR
ScrollTrigger.create({
  start: "top top", end: "max",
  onUpdate: (self) => {
    gsap.to(".progress-bar", { scaleX: self.progress, ease: "none" });
  }
});

// 5. REDUCED MOTION RESPECT
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (prefersReducedMotion) {
  gsap.globalTimeline.timeScale(0); // Skip all animations
}
```

---

## 📐 COMPONENT SPECIFICATIONS (No Placeholders)

### Hero Dashboard Mock (Glassmorphic, Real Data)
```html
<div class="hero-card" data-tilt data-tilt-max="8" data-tilt-glare data-tilt-max-glare="0.2">
  <div class="card-header">
    <span class="dot green"></span>
    <span class="card-title">ATS Admin Dashboard</span>
    <span class="badge">Admin Panel</span>
  </div>
  <div class="metrics-row">
    <div class="metric"><span class="num">6</span><small>Orgs</small></div>
    <div class="metric"><span class="num">17</span><small>Courses</small></div>
    <div class="metric highlight"><span class="num">81%</span><small>Score</small></div>
  </div>
  <div class="learner-list">
    <div class="learner-row"><span>Ratan Singh</span><div class="bar" style="width:68%"></div><span>68%</span></div>
    <div class="learner-row"><span>Priya Seth</span><div class="bar" style="width:82%"></div><span>82%</span></div>
    <div class="learner-row"><span>Amey Titty</span><div class="bar warn" style="width:41%"></div><span>41%</span></div>
    <div class="learner-row"><span>Sara Verma</span><div class="bar" style="width:75%"></div><span>75%</span></div>
  </div>
  <div class="card-footer">
    <span>1 pending enrollment</span>
    <span class="link">2 at-risk learners →</span>
  </div>
</div>
```

### Lottie Animation Sources (Free, No Placeholder)
```
- Analytics/Charts: https://lottiefiles.com/animations/chart-analytics
- Sync/Integration: https://lottiefiles.com/animations/sync-loading  
- Users/Team: https://lottiefiles.com/animations/team-collaboration
- Shield/Security: https://lottiefiles.com/animations/security-shield
- Content/Courses: https://lottiefiles.com/animations/online-learning
- Enrollment: https://lottiefiles.com/animations/form-submission
```

### Testimonial Data (Real, from screenshot)
```javascript
const testimonials = [
  {
    name: "Rohan Kumar",
    role: "L&D Manager, Infosys",
    stars: 5,
    quote: "The role-based dashboards made a huge difference. Our admins now manage their category independently without stepping on each other."
  },
  {
    name: "Sunita Arora", 
    role: "Training Lead, NovaTech",
    stars: 5,
    quote: "PAL tracking gave us visibility we never had before. We caught at-risk students early and improved completion rates by 22%."
  },
  {
    name: "Vikram Pillai",
    role: "CTO, EduBridge",
    stars: 5,
    quote: "We migrated from bare Moodle in under a week. The enrollment workflows and verification system saved hours of manual admin work."
  }
];
```

### Pricing Data (Real, from screenshot)
```javascript
const plans = [
  {
    name: "Starter",
    price: { monthly: "Free", annual: "Free" },
    tag: "For small teams",
    features: ["Up to 25 learners", "1 learning category", "5 courses", "Basic analytics", "Email support"]
  },
  {
    name: "Pro",
    price: { monthly: "₹2,499", annual: "₹1,999" },
    tag: "Most popular — per month",
    highlight: true,
    features: ["Up to 500 learners", "5 learning categories", "Unlimited courses", "PAL tracking and reports", "Moodle integration", "Bulk verification tools", "Priority support"]
  },
  {
    name: "Enterprise",
    price: { monthly: "Custom", annual: "Custom" },
    tag: "Contact sales",
    features: ["Unlimited learners", "Unlimited categories", "Custom domain", "SSO and LDAP", "Dedicated account manager", "SLA guarantee"]
  }
];
```

---

## 🔑 CRITICAL IMPLEMENTATION RULES

1. **NO placeholder images** — use CSS-drawn illustrations, Lottie animations, or Spline 3D scenes
2. **ALL text is real content** — copied from the original screenshot (no lorem ipsum)
3. **Animation performance**: `will-change: transform` on animated elements; use `transform` not `top/left`
4. **Mobile**: Vanta effects disabled on mobile (check `window.innerWidth < 768`); reduced parallax depth
5. **Fonts**: Load from Fontshare — `https://api.fontshare.com/v2/css?f[]=clash-display@600,700&f[]=cabinet-grotesk@400,500,700&display=swap`
6. **Color system**: Use CSS custom properties that mirror the admin console exactly
7. **Scroll trigger cleanup**: `ScrollTrigger.refresh()` after fonts load
8. **GSAP**: Register all plugins at top — `gsap.registerPlugin(ScrollTrigger, TextPlugin)`

---

## 🎬 RENDER ORDER / DOM LOAD SEQUENCE

```
1. HTML parses → skeleton visible instantly (no FOUC)
2. CSS loads → layout snaps into place
3. Fonts load → ScrollTrigger.refresh()
4. GSAP loads → animate loader bar 0→100%
5. Three.js + Vanta loads → hero background activates
6. Lottie loads → feature card animations ready
7. Vanilla Tilt loads → 3D tilt on all [data-tilt] elements
8. Typed.js loads → typewriter begins in hero
9. Splitting.js → char arrays built for all headings
10. ScrollTrigger → all scroll animations registered
```

---

## 📋 FINAL DELIVERABLE CHECKLIST

- [ ] Navbar: transparent → frosted scroll transition + magnetic links
- [ ] Hero: Vanta NET dark bg + Typed.js headline + floating tilt dashboard card + GSAP stagger entrance + parallax on scroll
- [ ] Features: Lottie icon hover animations + Vanilla Tilt cards + scroll reveal stagger
- [ ] Solutions: Tab switch with GSAP crossfade + Spline/Vanta right column
- [ ] How It Works: Line draw animation + step card stagger
- [ ] Testimonials: CSS infinite marquee + tilt cards
- [ ] Pricing: Glowing Pro card + toggle price flip + scroll reveal
- [ ] CTA: Vanta WAVES + magnetic buttons + text scramble
- [ ] Footer: Dark themed, hover underline draw
- [ ] Global: Custom cursor, scroll progress bar, page load sequence, reduced-motion fallback

---

*Generated by: Design Engineer + Prompt Engineer*  
*Target output: Single-file HTML — production-grade, zero placeholders, cinematic motion*
