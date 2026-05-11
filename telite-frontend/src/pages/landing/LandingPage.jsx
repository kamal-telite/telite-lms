import { useEffect } from "react";
import { Link } from "react-router-dom";
import { getDefaultRoute } from "../../context/session";
import "../../styles/landing.css";

const FEATURES = [
  { title: "Role-based access control", desc: "Separate dashboards for super admins, category admins, and learners. Every user sees exactly what they need.", bg: "bg-indigo-50", stroke: "#4f46e5", icon: <><circle cx="8" cy="6" r="3"/><path d="M2 14c0-3 3-5 6-5s6 2 6 5"/></> },
  { title: "Course and content management", desc: "Create, organise, and publish courses with module-level control. Manage tiers, statuses, and learner access in real time.", bg: "bg-teal-50", stroke: "#0d9488", icon: <><rect x="2" y="3" width="12" height="10" rx="1"/><path d="M5 7h6M5 10h4"/></> },
  { title: "Analytics and progress tracking", desc: "Real-time PAL scores, quiz averages, completion rates, and leaderboards. Identify at-risk learners before they fall behind.", bg: "bg-amber-50", stroke: "#d97706", icon: <><path d="M2 13V7l4-4 3 3 5-6"/></> },
  { title: "Moodle and API integration", desc: "Sync categories, courses, and users directly with Moodle. Open API support for third-party integrations.", bg: "bg-indigo-50", stroke: "#4f46e5", icon: <><rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/><rect x="2" y="9" width="5" height="5" rx="1"/><path d="M11.5 9v6M9 11.5h5"/></> },
  { title: "Enrollment management", desc: "Manual and self-enrollment flows with approval queues, domain-based access control, and bulk CSV verification.", bg: "bg-teal-50", stroke: "#0d9488", icon: <><path d="M8 2v12M3 7l5-5 5 5"/><path d="M1 14h14"/></> },
  { title: "Scalable multi-category architecture", desc: "Run ATS, DevOps, Cloud, and more as isolated categories — each with its own admin, courses, and learner pool.", bg: "bg-amber-50", stroke: "#d97706", icon: <><path d="M2 4h12M2 8h8M2 12h10"/><rect x="10" y="6" width="4" height="7" rx="1"/></> },
];
const COLLEGES = ["Manage students, courses, and departments","Academic analytics and attendance tracking","Role-based access per faculty and staff","Bulk enrollment and verification tools","Moodle integration for existing systems"];
const COMPANIES = ["Onboarding and compliance training paths","Skill tracking and certification management","Team-level performance dashboards","Domain-restricted signup and access control","Export reports as CSV or PDF"];
const STEPS = [
  { n: "1", title: "Create your workspace", desc: "Set up your organisation, configure allowed domains, and invite your first admins. Under five minutes." },
  { n: "2", title: "Add users and courses", desc: "Bulk-import learners, create learning categories, publish courses with modules, and assign tasks." },
  { n: "3", title: "Track and optimise", desc: "Monitor real-time progress, PAL scores, and completion rates. Export reports and act on at-risk alerts." },
];
const TESTIMONIALS = [
  { q: "The role-based dashboards made a huge difference. Our admins now manage their category independently without stepping on each other.", name: "Rohan Kumar", role: "L&D Head, TechCorp India", initials: "RK", bg: "bg-indigo-100", fg: "text-indigo-700" },
  { q: "PAL tracking gave us visibility we never had before. We caught at-risk students early and improved completion rates by 22%.", name: "Sunita Arora", role: "Academic Director, Nexus College", initials: "SA", bg: "bg-teal-100", fg: "text-teal-700" },
  { q: "We migrated from bare Moodle in under a week. The enrollment workflows and verification system saved hours of manual admin work.", name: "Vikram Pillai", role: "CTO, Skill Forward", initials: "VP", bg: "bg-amber-100", fg: "text-amber-700" },
];
const PLANS = [
  { name: "Starter", price: "Free", period: "forever", desc: "For small teams and individual instructors getting started.", features: ["Up to 25 learners","1 learning category","5 courses","Basic analytics","Email support"], featured: false, cta: "Get started", link: "/signup" },
  { name: "Pro", price: "₹2,499", period: "per month · billed annually", desc: "For growing organisations with multi-category and advanced analytics.", features: ["Up to 500 learners","5 learning categories","Unlimited courses","PAL tracking and reports","Moodle integration","Bulk verification tools","Priority support"], featured: true, cta: "Start 14-day trial", link: "/signup" },
  { name: "Enterprise", price: "Custom", period: "talk to sales", desc: "For colleges and large enterprises with compliance needs.", features: ["Unlimited learners","Unlimited categories","Custom domain","SSO and LDAP","Dedicated account manager","SLA guarantee"], featured: false, cta: "Contact sales", link: null },
];

function SectionHeader({ eyebrow, title, sub }) {
  return (
    <div className="text-center mb-14">
      <p className="text-indigo-600 text-xs font-semibold uppercase tracking-widest mb-3">{eyebrow}</p>
      <h2 className="text-3xl font-bold text-slate-900 mb-3">{title}</h2>
      {sub && <p className="text-slate-500 text-base leading-relaxed max-w-xl mx-auto">{sub}</p>}
    </div>
  );
}

function CheckItem({ text, color }) {
  return (
    <li className="flex items-start gap-3 py-2 text-sm text-slate-600 border-b border-slate-100 last:border-0">
      <svg className="w-4 h-4 mt-0.5 flex-shrink-0" viewBox="0 0 16 16" fill="none" stroke={color} strokeWidth="2"><path d="M3 8l3 3 7-7"/></svg>
      {text}
    </li>
  );
}

export default function LandingPage({ session }) {
  const dashboardLink = session?.user ? getDefaultRoute(session.user) : null;

  useEffect(() => {
    const handler = () => {
      const nav = document.getElementById("lp-nav");
      if (nav) nav.classList.toggle("lp-nav--scrolled", window.scrollY > 10);
    };
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <div className="bg-[#FAFAFA] text-[#1A1A2E]" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
      {/* ── NAVBAR ── */}
      <nav id="lp-nav" className="sticky top-0 z-50 border-b border-[#E8E8F0] bg-white/80 backdrop-blur transition-all duration-200">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="text-lg font-semibold text-indigo-600 tracking-tight">Telite LMS</span>
          <div className="hidden md:flex items-center gap-1">
            {["Home","Features","Solutions","Pricing","About","Contact"].map(l => (
              <a key={l} href={l === "Home" ? "#" : `#${l.toLowerCase()}`} className="text-sm text-slate-600 hover:text-indigo-600 px-3 py-2 rounded-md transition-all duration-200">{l}</a>
            ))}
          </div>
          <div className="flex items-center gap-2">
            {dashboardLink ? (
              <Link to={dashboardLink} className="text-sm font-medium bg-indigo-600 text-white px-5 py-2 rounded-lg hover:bg-indigo-700 transition-all duration-200">Go to Dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="text-sm text-slate-600 hover:text-indigo-700 px-3 py-2 transition-all duration-200">Sign in</Link>
                <Link to="/signup" className="text-sm font-medium bg-indigo-600 text-white px-5 py-2 rounded-lg hover:bg-indigo-700 transition-all duration-200">Sign up free</Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="min-h-[calc(100vh-56px)] flex items-center">
        <div className="max-w-7xl mx-auto px-6 py-20 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <p className="text-indigo-600 text-xs font-semibold uppercase tracking-widest mb-4">Internal learning platform</p>
            <h1 className="text-4xl md:text-5xl font-bold leading-tight text-slate-900 max-w-xl">One platform to manage learning, users, analytics, and content delivery.</h1>
            <p className="text-slate-500 text-lg leading-relaxed mt-4 max-w-lg">Streamline education and training with role-based dashboards, real-time tracking, and seamless LMS integration.</p>
            <div className="flex flex-wrap gap-3 mt-8">
              {dashboardLink ? (
                <Link to={dashboardLink} className="bg-indigo-600 text-white px-7 py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-all duration-200 shadow-sm">Go to Dashboard</Link>
              ) : (
                <Link to="/signup" className="bg-indigo-600 text-white px-7 py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-all duration-200 shadow-sm">Get started free</Link>
              )}
              <a href="#features" className="border border-slate-300 text-slate-700 px-7 py-3 rounded-xl hover:border-indigo-400 hover:text-indigo-600 transition-all duration-200">Explore features</a>
            </div>
            <div className="flex items-center gap-3 mt-10">
              <span className="text-xs text-slate-400">Trusted by</span>
              {["Colleges","Companies","Training institutes"].map(t => (
                <span key={t} className="bg-indigo-50 text-indigo-700 text-xs px-3 py-1 rounded-full border border-indigo-200">{t}</span>
              ))}
            </div>
          </div>
          {/* Dashboard mockup */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100">
              <div className="w-3 h-3 rounded-full bg-red-400"/>
              <div className="w-3 h-3 rounded-full bg-amber-400"/>
              <div className="w-3 h-3 rounded-full bg-green-400"/>
              <span className="text-sm font-medium text-slate-700 ml-1">ATS Admin Dashboard</span>
              <span className="ml-auto bg-indigo-50 text-indigo-600 text-xs px-2 py-0.5 rounded-full">admin panel</span>
            </div>
            <div className="grid" style={{ gridTemplateColumns: "100px 1fr" }}>
              <div className="bg-slate-50 border-r border-slate-100 py-3 px-2">
                {["Dashboard","Courses","Learners","Enrollment","PAL tracking","Reports"].map((s,i) => (
                  <div key={s} className={`text-xs px-2 py-1.5 rounded-md mb-0.5 ${i===0 ? "bg-indigo-50 text-indigo-700 font-medium" : "text-slate-500"}`}>{s}</div>
                ))}
              </div>
              <div className="p-4">
                <div className="grid grid-cols-3 gap-2 mb-4">
                  {[["6","courses","text-indigo-600"],["17","learners","text-slate-800"],["81%","avg PAL","text-emerald-600"]].map(([v,l,c]) => (
                    <div key={l} className="bg-slate-50 rounded-lg p-2 text-center">
                      <div className={`text-lg font-semibold ${c}`}>{v}</div>
                      <div className="text-[10px] text-slate-400">{l}</div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-slate-400 mb-2">PAL score by student</p>
                {[["Rahul Singh",94,"bg-indigo-500","text-slate-400"],["Kavya Iyer",90,"bg-indigo-500","text-slate-400"],["Neha Pillai",88,"bg-indigo-400","text-slate-400"],["Dev Verma",54,"bg-red-400","text-red-500"]].map(([n,p,bar,tc]) => (
                  <div key={n} className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs text-slate-600 w-[72px] truncate">{n}</span>
                    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden"><div className={`h-full rounded-full ${bar}`} style={{ width: `${p}%` }}/></div>
                    <span className={`text-xs w-7 text-right ${tc}`}>{p}%</span>
                  </div>
                ))}
                <div className="flex gap-1.5 mt-3">
                  <span className="bg-amber-50 text-amber-700 text-[10px] px-2 py-0.5 rounded">3 pending enrollments</span>
                  <span className="bg-red-50 text-red-600 text-[10px] px-2 py-0.5 rounded">2 at-risk learners</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section id="features" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <SectionHeader eyebrow="Everything you need" title="Built for modern learning operations" sub="A complete toolkit for admins, instructors, and learners."/>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(f => (
              <div key={f.title} className="bg-white border border-slate-100 rounded-2xl p-6 hover:border-indigo-200 hover:shadow-sm transition-all duration-200">
                <div className={`w-10 h-10 rounded-xl ${f.bg} flex items-center justify-center mb-4`}>
                  <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke={f.stroke} strokeWidth="1.5">{f.icon}</svg>
                </div>
                <h3 className="text-sm font-semibold text-slate-800 mb-2">{f.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SOLUTIONS ── */}
      <section id="solutions" className="py-24 bg-slate-50">
        <div className="max-w-7xl mx-auto px-6">
          <SectionHeader eyebrow="Solutions" title="Built for your context" sub="Whether managing students across departments or training employees at scale."/>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <div className="bg-white border border-slate-200 rounded-2xl p-8">
              <span className="inline-block bg-indigo-100 text-indigo-700 text-xs font-medium px-3 py-1 rounded-full mb-4">For colleges</span>
              <h3 className="text-lg font-semibold text-slate-800 mb-4">Academic learning management</h3>
              <ul className="space-y-0">{COLLEGES.map(c => <CheckItem key={c} text={c} color="#4f46e5"/>)}</ul>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-8">
              <span className="inline-block bg-teal-100 text-teal-700 text-xs font-medium px-3 py-1 rounded-full mb-4">For companies</span>
              <h3 className="text-lg font-semibold text-slate-800 mb-4">Employee training and upskilling</h3>
              <ul className="space-y-0">{COMPANIES.map(c => <CheckItem key={c} text={c} color="#0d9488"/>)}</ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <SectionHeader eyebrow="How it works" title="Up and running in three steps" sub="No complex setup. Your team can be learning within hours."/>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative max-w-4xl mx-auto">
            <div className="hidden md:block absolute top-6 left-[16.66%] right-[16.66%] h-px bg-slate-200 z-0" style={{ marginLeft: 24, marginRight: 24 }}/>
            {STEPS.map(s => (
              <div key={s.n} className="text-center relative z-10">
                <div className="w-12 h-12 rounded-full bg-indigo-50 border-2 border-indigo-200 flex items-center justify-center mx-auto mb-4 text-indigo-700 font-semibold text-lg">{s.n}</div>
                <h3 className="font-semibold text-slate-800 mb-2">{s.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed max-w-[220px] mx-auto">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ── */}
      <section className="py-24 bg-slate-50">
        <div className="max-w-7xl mx-auto px-6">
          <SectionHeader eyebrow="Testimonials" title="Trusted by learning teams"/>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {TESTIMONIALS.map(t => (
              <div key={t.name} className="bg-white border border-slate-100 rounded-2xl p-6">
                <div className="flex gap-1 mb-4">{[...Array(5)].map((_,i) => <div key={i} className="w-3 h-3 bg-amber-400 rounded-sm"/>)}</div>
                <p className="text-slate-600 text-sm leading-relaxed mb-4">"{t.q}"</p>
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full ${t.bg} ${t.fg} flex items-center justify-center text-xs font-medium`}>{t.initials}</div>
                  <div><div className="text-sm font-semibold">{t.name}</div><div className="text-xs text-slate-400">{t.role}</div></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PRICING ── */}
      <section id="pricing" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <SectionHeader eyebrow="Pricing" title="Simple, transparent pricing" sub="Start free. Scale as you grow. No hidden fees."/>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {PLANS.map(p => (
              <div key={p.name} className={`bg-white rounded-2xl p-8 relative ${p.featured ? "border-2 border-indigo-600" : "border border-slate-200"}`}>
                {p.featured && <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs px-4 py-1 rounded-full whitespace-nowrap">Most popular</span>}
                <p className={`text-xs font-semibold uppercase tracking-wider mb-2 ${p.featured ? "text-indigo-600" : "text-slate-500"}`}>{p.name}</p>
                <div className="text-3xl font-bold text-slate-900">{p.price}</div>
                <p className="text-xs text-slate-400 mb-4">{p.period}</p>
                <p className="text-sm text-slate-500 mb-5 leading-relaxed">{p.desc}</p>
                <hr className="border-slate-100 mb-4"/>
                <ul className="space-y-2 mb-6">{p.features.map(f => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-600"><span className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"/>{f}</li>
                ))}</ul>
                {p.link ? (
                  <Link to={dashboardLink || p.link} className={`block w-full text-center py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${p.featured ? "bg-indigo-600 text-white hover:bg-indigo-700" : "border border-slate-300 text-slate-700 hover:border-indigo-400 hover:text-indigo-600"}`}>
                    {dashboardLink ? "Go to Dashboard" : p.cta}
                  </Link>
                ) : (
                  <button className="w-full py-2.5 rounded-lg text-sm border border-slate-300 text-slate-700 hover:border-indigo-400 hover:text-indigo-600 transition-all duration-200">{p.cta}</button>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ── */}
      <section className="py-20 bg-indigo-600">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-white">Ready to modernise your learning operations?</h2>
          <p className="text-indigo-200 mt-3 mb-8">Join hundreds of colleges and companies already using Telite LMS.</p>
          <div className="flex justify-center gap-4 flex-wrap">
            {dashboardLink ? (
              <Link to={dashboardLink} className="bg-white text-indigo-700 font-semibold px-8 py-3 rounded-xl hover:bg-indigo-50 transition-all duration-200">Go to Dashboard</Link>
            ) : (
              <Link to="/signup" className="bg-white text-indigo-700 font-semibold px-8 py-3 rounded-xl hover:bg-indigo-50 transition-all duration-200">Get started free</Link>
            )}
            <button className="border border-indigo-400 text-white px-8 py-3 rounded-xl hover:bg-indigo-700 transition-all duration-200">Book a demo</button>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="bg-slate-900 py-14">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
            <div>
              <h4 className="text-white font-semibold text-lg">Telite LMS</h4>
              <p className="text-slate-400 text-sm mt-2 leading-relaxed">Role-aware learning operations for colleges, companies, and training institutes.</p>
            </div>
            {[
              { title: "Product", items: ["Features","Pricing","Changelog","Roadmap","API docs"] },
              { title: "Company", items: ["About","Blog","Careers","Press kit"] },
              { title: "Support", items: ["Help centre","Contact us","Privacy policy","Terms of service"] },
            ].map(col => (
              <div key={col.title}>
                <h5 className="text-slate-300 text-sm font-semibold mb-3">{col.title}</h5>
                <ul className="space-y-2">{col.items.map(i => <li key={i}><a className="text-slate-400 text-sm hover:text-white transition-all duration-200 cursor-pointer">{i}</a></li>)}</ul>
              </div>
            ))}
          </div>
          <div className="flex flex-col md:flex-row justify-between items-center border-t border-slate-800 mt-10 pt-6 gap-4">
            <p className="text-slate-500 text-sm">© 2026 Telite Systems. All rights reserved.</p>
            <div className="flex gap-2">
              {[
                <><path d="M9 2H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8"/><path d="M7 7l7-7M10 1h4v4"/></>,
                <><path d="M4 1h2a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H4a3 3 0 0 1-3-3V4a3 3 0 0 1 3-3z"/><path d="M10 1h2v4l-2 2-2-2V1z"/></>,
                <><rect x="1" y="3" width="12" height="10" rx="1"/><path d="M1 3l6 5 6-5"/></>,
              ].map((svg, i) => (
                <div key={i} className="w-8 h-8 rounded-lg border border-slate-700 flex items-center justify-center hover:border-slate-500 hover:bg-slate-800 transition-all duration-200 cursor-pointer">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 14 14" fill="none" stroke="#94a3b8" strokeWidth="1.5">{svg}</svg>
                </div>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
