import { useEffect, useRef, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { getDefaultRoute } from "../../context/session";
import CommandPalette from "./components/CommandPalette";
import "../../styles/landing.css";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title as ChartTitle,
  Tooltip,
  Legend,
  Filler
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ChartTitle,
  Tooltip,
  Legend,
  Filler
);

const FEATURES = [
  { id: "rbac", title: "Role-based access control", desc: "Separate dashboards for super admins, category admins, and learners. Every user sees exactly what they need.", svg: <svg viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#4648d4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg> },
  { id: "course", title: "Course and content management", desc: "Create, organise, and publish courses with module-level control. Manage tiers, statuses, and learner access in real time.", svg: <svg viewBox="0 0 24 24" fill="none"><path d="M4 6h16M4 10h16M4 14h10" stroke="#4648d4" strokeWidth="2" strokeLinecap="round"/><rect x="4" y="2" width="16" height="20" rx="2" stroke="#4648d4" strokeWidth="2"/></svg> },
  { id: "analytics", title: "Analytics and progress tracking", desc: "Real-time PAL scores, quiz averages, completion rates, and leaderboards. Identify at-risk learners before they fall behind.", svg: <svg viewBox="0 0 24 24" fill="none"><path d="M3 3v18h18" stroke="#4648d4" strokeWidth="2" strokeLinecap="round"/><path d="M18 9l-5 5-3-3-4 4" stroke="#4648d4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg> },
  { id: "moodle", title: "Moodle and API integration", desc: "Sync categories, courses, and users directly with Moodle. Open API support for third-party integrations.", svg: <svg viewBox="0 0 24 24" fill="none"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" stroke="#4648d4" strokeWidth="2"/><path d="M12 8v4l3 3" stroke="#4648d4" strokeWidth="2" strokeLinecap="round"/></svg> },
  { id: "enrollment", title: "Enrollment management", desc: "Manual and self-enrollment flows with approval queues, domain-based access control, and built-in CSV verification.", svg: <svg viewBox="0 0 24 24" fill="none"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="#4648d4" strokeWidth="2" strokeLinecap="round"/><circle cx="9" cy="7" r="4" stroke="#4648d4" strokeWidth="2"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" stroke="#4648d4" strokeWidth="2" strokeLinecap="round"/></svg> },
  { id: "scale", title: "Scalable multi-category architecture", desc: "Run ATS, DevOps, Cloud and more as isolated categories - each with its own admin, courses, and learner pool.", svg: <svg viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="7" rx="1" stroke="#4648d4" strokeWidth="2"/><rect x="14" y="3" width="7" height="7" rx="1" stroke="#4648d4" strokeWidth="2"/><rect x="3" y="14" width="7" height="7" rx="1" stroke="#4648d4" strokeWidth="2"/><rect x="14" y="14" width="7" height="7" rx="1" stroke="#4648d4" strokeWidth="2"/></svg> },
];

const TESTIMONIALS = [
  { name: "Rohan Kumar", role: "L&D Manager, Infosys", stars: 5, quote: "The role-based dashboards made a huge difference. Our admins now manage their category independently without stepping on each other." },
  { name: "Sunita Arora", role: "Training Lead, NovaTech", stars: 5, quote: "PAL tracking gave us visibility we never had before. We caught at-risk students early and improved completion rates by 22%." },
  { name: "Vikram Pillai", role: "CTO, EduBridge", stars: 5, quote: "We migrated from bare Moodle in under a week. The enrollment workflows and verification system saved hours of manual admin work." },
  { name: "Deepa Nair", role: "Academic Dean, MIT Pune", stars: 5, quote: "Finally a platform that understands how colleges actually operate. The multi-category structure maps perfectly to our departments." },
  { name: "Arjun Mehta", role: "HR Director, FinEdge", stars: 5, quote: "Onboarding compliance training used to take weeks to set up. With Telite, our new cohort was live in a day. Genuinely surprised." },
  { name: "Priya Shah", role: "VP Learning, Cybertech", stars: 5, quote: "The analytics dashboard alone is worth the upgrade. Seeing PAL scores and quiz trends in real time changed how our managers coach teams." },
];

const PLANS = [
  { name: "Starter", price: { monthly: "Free", annual: "Free" }, tag: "For small teams and individual instructors getting started", period: "No credit card required", features: ["Up to 25 learners", "1 learning category", "5 courses", "Basic analytics", "Email support"] },
  { name: "Pro", price: { monthly: "₹2,499", annual: "₹1,999" }, tag: "For growing organisations with multi-category and advanced analytics", period: "per month, billed monthly", highlight: true, features: ["Up to 500 learners", "5 learning categories", "Unlimited courses", "PAL tracking and reports", "Moodle integration", "Bulk verification tools", "Priority support"] },
  { name: "Enterprise", price: { monthly: "Custom", annual: "Custom" }, tag: "For colleges and large enterprises with compliance needs", period: "Talk to us", features: ["Unlimited learners", "Unlimited categories", "Custom domain", "SSO and LDAP", "Dedicated account manager", "SLA guarantee"] },
];

const TRUST_LOGOS = [
  {
    name: "IIT Bombay",
    svg: (
      <svg className="trust-logo-svg" viewBox="0 0 200 60" fill="currentColor">
        <text x="50%" y="38" fontSize="22" fontWeight="800" textAnchor="middle" fontFamily="var(--font-display)">IIT BOMBAY</text>
        <circle cx="25" cy="30" r="8" stroke="currentColor" strokeWidth="2" fill="none"/>
        <line x1="25" y1="18" x2="25" y2="42" stroke="currentColor" strokeWidth="2"/>
        <line x1="13" y1="30" x2="37" y2="30" stroke="currentColor" strokeWidth="2"/>
      </svg>
    )
  },
  {
    name: "MIT Pune",
    svg: (
      <svg className="trust-logo-svg" viewBox="0 0 200 60" fill="currentColor">
        <text x="50%" y="38" fontSize="22" fontWeight="800" textAnchor="middle" fontFamily="var(--font-display)">MIT PUNE</text>
        <path d="M20 20 L28 35 L36 20 M28 35 L28 42" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
      </svg>
    )
  },
  {
    name: "Infosys",
    svg: (
      <svg className="trust-logo-svg" viewBox="0 0 200 60" fill="currentColor">
        <text x="50%" y="38" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="var(--font-body)" letterSpacing="0.05em">Infosys</text>
        <path d="M15 20 H35 V24 H15 V20 Z M15 28 H35 V32 H15 V28 Z M15 36 H30 V40 H15 V36 Z" fill="currentColor"/>
      </svg>
    )
  },
  {
    name: "TCS",
    svg: (
      <svg className="trust-logo-svg" viewBox="0 0 200 60" fill="currentColor">
        <text x="50%" y="38" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="var(--font-display)" letterSpacing="0.02em">tcs</text>
        <path d="M15 22 C15 22 23 15 32 25 C32 25 24 35 15 22 Z" fill="currentColor" opacity="0.8"/>
      </svg>
    )
  },
  {
    name: "NovaTech",
    svg: (
      <svg className="trust-logo-svg" viewBox="0 0 200 60" fill="currentColor">
        <text x="50%" y="38" fontSize="20" fontWeight="700" textAnchor="middle" fontFamily="var(--font-body)">NovaTech</text>
        <polygon points="25,18 35,35 15,35" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
        <circle cx="25" cy="28" r="3" fill="currentColor"/>
      </svg>
    )
  },
  {
    name: "EduBridge",
    svg: (
      <svg className="trust-logo-svg" viewBox="0 0 200 60" fill="currentColor">
        <text x="50%" y="38" fontSize="20" fontWeight="700" textAnchor="middle" fontFamily="var(--font-body)">EduBridge</text>
        <rect x="15" y="20" width="20" height="20" rx="4" stroke="currentColor" strokeWidth="2" fill="none"/>
        <line x1="25" y1="20" x2="25" y2="40" stroke="currentColor" strokeWidth="2"/>
      </svg>
    )
  },
  {
    name: "FinEdge",
    svg: (
      <svg className="trust-logo-svg" viewBox="0 0 200 60" fill="currentColor">
        <text x="50%" y="38" fontSize="20" fontWeight="700" textAnchor="middle" fontFamily="var(--font-body)">FinEdge</text>
        <path d="M15 35 L25 20 L35 35 Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
        <line x1="18" y1="30" x2="32" y2="30" stroke="currentColor" strokeWidth="2"/>
      </svg>
    )
  },
  {
    name: "Cybertech",
    svg: (
      <svg className="trust-logo-svg" viewBox="0 0 200 60" fill="currentColor">
        <text x="50%" y="38" fontSize="20" fontWeight="700" textAnchor="middle" fontFamily="var(--font-body)">Cybertech</text>
        <rect x="18" y="20" width="16" height="20" rx="3" fill="none" stroke="currentColor" strokeWidth="2"/>
        <path d="M22 20 V16 C22 14 26 14 26 16 V20" stroke="currentColor" strokeWidth="2" fill="none"/>
      </svg>
    )
  }
];

const INTEGRATIONS = [
  {
    name: "Moodle",
    category: "LMS",
    desc: "High-speed bi-directional course category synchronization and user enrollment.",
    status: "Available",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
        <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5" />
      </svg>
    )
  },
  {
    name: "Zoom",
    category: "Communication",
    desc: "Auto-provision lecture rooms, generate attendance logs, and embed meetings.",
    status: "Available",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M23 7l-7 5 7 5V7z" />
        <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
      </svg>
    )
  },
  {
    name: "Slack",
    category: "Communication",
    desc: "Push event updates, automated reminders, and grade notifications to channels.",
    status: "Available",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" />
      </svg>
    )
  },
  {
    name: "MS Teams",
    category: "Communication",
    desc: "Integrate student groups, sync Microsoft Outlook calendars, and stream lectures.",
    status: "Available",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 00-3-3.87" />
        <path d="M16 3.13a4 4 0 010 7.75" />
      </svg>
    )
  },
  {
    name: "Razorpay",
    category: "Payments",
    desc: "Process course sales, automate student fee payouts, and reconcile invoices.",
    status: "Available",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="5" width="20" height="14" rx="2" />
        <line x1="2" y1="10" x2="22" y2="10" />
      </svg>
    )
  },
  {
    name: "Google Workspace",
    category: "Enterprise",
    desc: "Single Sign-On (SSO) login flow and direct document attachment via Google Drive.",
    status: "Available",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
        <path d="M2 12h20" />
      </svg>
    )
  },
  {
    name: "Google Classroom",
    category: "LMS",
    desc: "Import course curricula, gradebooks, and synchronize active student directories.",
    status: "Coming Soon",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
      </svg>
    )
  },
  {
    name: "Stripe",
    category: "Payments",
    desc: "Enable international payment gateways, dynamic taxes, and recurring subscriptions.",
    status: "Coming Soon",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" />
        <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
      </svg>
    )
  },
  {
    name: "LDAP / AD SSO",
    category: "Enterprise",
    desc: "Secure login synchronization with institutional directories and on-premise servers.",
    status: "Coming Soon",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0110 0v4" />
      </svg>
    )
  }
];

const PREVIEW_CHART_DATA = {
  labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  datasets: [
    {
      label: "Live Engagement",
      data: [65, 78, 90, 85, 95, 110, 105],
      borderColor: "#6366f1", // primary
      backgroundColor: "rgba(99, 102, 241, 0.1)",
      borderWidth: 3,
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      pointBackgroundColor: "#05050a",
      pointBorderColor: "#6366f1",
      pointBorderWidth: 2,
    },
    {
      label: "Cognitive Fatigue Risk",
      data: [20, 15, 30, 25, 10, 5, 8],
      borderColor: "#f59e0b", // amber
      backgroundColor: "rgba(245, 158, 11, 0.1)",
      borderWidth: 2,
      borderDash: [5, 5],
      fill: false,
      tension: 0.4,
      pointRadius: 0,
    }
  ]
};

const PREVIEW_CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "top",
      labels: {
        color: "rgba(255, 255, 255, 0.7)",
        font: { family: "Cabinet Grotesk, sans-serif", size: 12 }
      }
    },
    tooltip: {
      backgroundColor: "rgba(17, 16, 39, 0.95)",
      titleColor: "#fff",
      bodyColor: "rgba(255, 255, 255, 0.8)",
      borderColor: "rgba(255, 255, 255, 0.1)",
      borderWidth: 1,
    }
  },
  scales: {
    x: {
      grid: { color: "rgba(255, 255, 255, 0.05)" },
      ticks: { color: "rgba(255, 255, 255, 0.5)", font: { family: "Cabinet Grotesk" } }
    },
    y: {
      grid: { color: "rgba(255, 255, 255, 0.05)" },
      ticks: { color: "rgba(255, 255, 255, 0.5)", font: { family: "Cabinet Grotesk" } }
    }
  }
};

function CountUp({ target, suffix = "", prefix = "", decimals = 0, useSeparator = true }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    let active = true;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && active) {
        let startTime = null;
        const duration = 1800; // 1.8 seconds

        const step = (currentTime) => {
          if (!startTime) startTime = currentTime;
          const progress = Math.min((currentTime - startTime) / duration, 1);
          // quadratic ease-out
          const easeOut = 1 - (1 - progress) * (1 - progress);
          const value = easeOut * target;
          
          setCount(value);
          if (progress < 1 && active) {
            requestAnimationFrame(step);
          } else {
            setCount(target);
          }
        };

        requestAnimationFrame(step);
        observer.disconnect();
      }
    }, { threshold: 0.1 });

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => {
      active = false;
      observer.disconnect();
    };
  }, [target]);

  const formattedValue = decimals > 0 
    ? count.toFixed(decimals) 
    : Math.floor(count);

  const displayValue = useSeparator && decimals === 0
    ? Number(formattedValue).toLocaleString()
    : formattedValue;

  return (
    <span ref={ref}>
      {prefix}
      {displayValue}
      {suffix}
    </span>
  );
}

const FAQS = [
  {
    q: "What exactly is Telite Systems LMS?",
    a: "Telite Systems LMS is a modern learning operations orchestrator and analytics layer built to sit alongside your Moodle runtime or run stand-alone. It provides premium role-based administrative consoles, custom organizational boundaries, and advanced AI-driven proactive analytics."
  },
  {
    q: "How does the Moodle integration work?",
    a: "Telite integrates seamlessly via high-speed Moodle REST Web Services APIs. It manages user accounts, course categories, metadata, and business operations, whilst Moodle reliably serves learning content and SCORM packages. No database customization or plugins are needed."
  },
  {
    q: "Is it compliant with modern security standards?",
    a: "Yes. We designed Telite with enterprise-grade protection. Data is encrypted at rest (AES-256) and in transit (TLS 1.3), supporting strict role hierarchies, row-level access control, and comprehensive logs tracking admin activities."
  },
  {
    q: "Can we customize branding for our institution?",
    a: "Absolutely. Our Enterprise tier supports full white-label capabilities: custom subdomains/domains, custom CSS styling/themes, logo sets, and localized email notifications to match your organization’s identity perfectly."
  },
  {
    q: "How long does setting up our workspace take?",
    a: "Workspaces are provisioned immediately upon sign-up. Setting up organizational categories, bulk importing learners, and synchronizing content via our setup wizards usually takes less than 15 minutes."
  }
];

function FAQItem({ item }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className={`faq-item ${isOpen ? "open" : ""}`}>
      <button className="faq-trigger" onClick={() => setIsOpen(!isOpen)} aria-expanded={isOpen}>
        <span className="faq-question">{item.q}</span>
        <span className="faq-icon-wrap">
          <svg className="faq-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </span>
      </button>
      <div className="faq-content-wrap" style={{ maxHeight: isOpen ? "300px" : "0" }}>
        <div className="faq-content">
          <p>{item.a}</p>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({ f }) {
  return (
    <div className="feature-card">
      <div className="fc-icon">{f.svg}</div>
      <h3 className="fc-title">{f.title}</h3>
      <p className="fc-desc">{f.desc}</p>
    </div>
  );
}

export default function LandingPage({ session }) {
  const dashboardLink = session?.user ? getDefaultRoute(session.user) : null;
  const [isAnnual, setIsAnnual] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("Pro");
  const [activeTab, setActiveTab] = useState("college");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const vantaHeroRef = useRef(null);
  const vantaCtaRef = useRef(null);
  const heroTypedRef = useRef(null);
  const cursorRef = useRef(null);
  const cursorDotRef = useRef(null);
  const priceRefsMap = useRef({});

  // Phase 3 states
  const [activeIntegrationTab, setActiveIntegrationTab] = useState("All");
  const [activePreviewTab, setActivePreviewTab] = useState("analytics");
  const [showStickyCTA, setShowStickyCTA] = useState(false);
  const [showContactModal, setShowContactModal] = useState(false);
  const [contactForm, setContactForm] = useState({ name: "", email: "", org: "", type: "College / University", msg: "" });
  const [contactError, setContactError] = useState("");
  const [contactSuccess, setContactSuccess] = useState(false);
  const [showSupportWidget, setShowSupportWidget] = useState(false);
  const [newsletterEmail, setNewsletterEmail] = useState("");
  const [newsletterSuccess, setNewsletterSuccess] = useState(false);

  // Theme toggle
  const toggleTheme = useCallback(() => {
    setIsDark(prev => {
      const next = !prev;
      document.documentElement.dataset.theme = next ? '' : 'light';
      document.body.style.background = next ? '#07006c' : '#f8f9ff';
      return next;
    });
  }, []);

  // Cmd+K keyboard shortcut for command palette
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const [approvals, setApprovals] = useState([
    { id: 1, name: "Varun Mehta", course: "Advanced Machine Learning", org: "IIT Bombay", status: "Pending" },
    { id: 2, name: "Sneha Nair", course: "React Design Patterns", org: "Infosys", status: "Pending" },
    { id: 3, name: "Aman Gupta", course: "Cloud Security Architecture", org: "NovaTech", status: "Pending" },
  ]);

  const [modules, setModules] = useState([
    { id: 1, title: "Module 1: Introduction & Environment Setup", duration: "2 hrs", active: true },
    { id: 2, title: "Module 2: Core Fundamentals & Syntax", duration: "4 hrs", active: true },
    { id: 3, title: "Module 3: Advanced Optimization & Scaling", duration: "5 hrs", active: false },
    { id: 4, title: "Module 4: Real-world Case Studies & Capstone", duration: "8 hrs", active: false }
  ]);

  const handleApprove = (id) => {
    setApprovals(prev => prev.map(app => app.id === id ? { ...app, status: "Approved" } : app));
  };
  const handleReject = (id) => {
    setApprovals(prev => prev.map(app => app.id === id ? { ...app, status: "Rejected" } : app));
  };

  const toggleModule = (id) => {
    setModules(prev => prev.map(m => m.id === id ? { ...m, active: !m.active } : m));
  };

  const handleContactSubmit = (e) => {
    e.preventDefault();
    if (!contactForm.name.trim()) {
      setContactError("Name is required");
      return;
    }
    if (!contactForm.email.includes("@")) {
      setContactError("Please enter a valid work email");
      return;
    }
    if (!contactForm.org.trim()) {
      setContactError("Organization name is required");
      return;
    }
    setContactError("");
    setContactSuccess(true);
    setTimeout(() => {
      setShowContactModal(false);
      setContactSuccess(false);
      setContactForm({ name: "", email: "", org: "", type: "College / University", msg: "" });
    }, 2500);
  };

  const handleNewsletterSubmit = (e) => {
    e.preventDefault();
    if (!newsletterEmail.includes("@")) return;
    setNewsletterSuccess(true);
    setNewsletterEmail("");
    setTimeout(() => setNewsletterSuccess(false), 3000);
  };

  // Toggle handler with price animation
  const handleToggle = () => {
    setIsAnnual((prev) => !prev);
    // Trigger price pop animation
    Object.values(priceRefsMap.current).forEach((el) => {
      if (el) {
        el.classList.remove("price-animate");
        // Force reflow
        void el.offsetWidth;
        el.classList.add("price-animate");
      }
    });
  };

  useEffect(() => {
    const gsap = window.gsap;
    const ScrollTrigger = window.ScrollTrigger;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const finePointer = window.matchMedia("(pointer: fine)").matches;
    const isDesktop = window.innerWidth >= 1100;
    const enablePointerEffects = !reduceMotion && finePointer && isDesktop;
    const enableDecorativeEngines = !reduceMotion && isDesktop && ((navigator.hardwareConcurrency || 4) >= 8);
    const revealPage = () => {
      document.querySelectorAll(".hero-eyebrow, .hero-headline, .hero-sub, .hero-ctas, .hero-badges, .hero-card-wrap, .feature-card, .step-card, .pricing-card").forEach((el) => {
        el.style.opacity = "1";
        el.style.transform = "none";
      });
    };
    const loaderFallback = window.setTimeout(() => {
      const loader = document.querySelector(".loader");
      if (loader) {
        loader.style.opacity = "0";
        loader.style.pointerEvents = "none";
        loader.style.display = "none";
      }
      revealPage();
    }, 2200);

    if (gsap && ScrollTrigger) gsap.registerPlugin(ScrollTrigger, window.TextPlugin);

    let mouseRaf = 0;
    let mousePoint = null;
    const handleMouseMove = (e) => {
      mousePoint = { x: e.clientX, y: e.clientY };
      if (mouseRaf) return;

      mouseRaf = window.requestAnimationFrame(() => {
        mouseRaf = 0;
        if (!mousePoint) return;

        if (cursorRef.current) {
          cursorRef.current.style.left = mousePoint.x + "px";
          cursorRef.current.style.top = mousePoint.y + "px";
        }
        if (cursorDotRef.current) {
          cursorDotRef.current.style.left = mousePoint.x + "px";
          cursorDotRef.current.style.top = mousePoint.y + "px";
        }

        const hero = document.getElementById("hero");
        if (hero) {
          const rect = hero.getBoundingClientRect();
          hero.style.setProperty("--mouse-x", `${mousePoint.x - rect.left}px`);
          hero.style.setProperty("--mouse-y", `${mousePoint.y - rect.top}px`);
        }
      });
    };
    if (enablePointerEffects) {
      document.addEventListener("mousemove", handleMouseMove, { passive: true });
    } else {
      if (cursorRef.current) cursorRef.current.style.display = "none";
      if (cursorDotRef.current) cursorDotRef.current.style.display = "none";
    }

    const pulseInterval = setInterval(() => {
      const metrics = document.querySelectorAll(".hc-metric");
      const random = metrics[Math.floor(Math.random() * metrics.length)];
      if (random && gsap) {
        gsap.fromTo(random, { scale: 1 }, { scale: 1.1, duration: 0.25, yoyo: true, repeat: 1, ease: "power2.inOut" });
      }
    }, 4000);

    const nav = document.getElementById("lp-nav");
    const handleScroll = () => {
      if (nav) nav.classList.toggle("scrolled", window.scrollY > 10);
      const hero = document.getElementById("hero");
      if (hero) {
        const rect = hero.getBoundingClientRect();
        setShowStickyCTA(rect.bottom < 0);
      }
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    let vantaHero = null;
    if (enableDecorativeEngines && window.VANTA?.NET) {
      vantaHero = window.VANTA.NET({
        el: vantaHeroRef.current,
        mouseControls: false,
        touchControls: false,
        gyroControls: false,
        minHeight: 200,
        minWidth: 200,
        scale: 1,
        scaleMobile: 1,
        color: 0x4648d4,
        backgroundColor: 0x00000000,
        points: 6,
        maxDistance: 14,
        spacing: 22,
      });
    }

    let vantaCta = null;
    if (enableDecorativeEngines && window.VANTA?.WAVES) {
      vantaCta = window.VANTA.WAVES({
        el: vantaCtaRef.current,
        mouseControls: false,
        touchControls: false,
        color: 0x3835a8,
        waveHeight: 12,
        shininess: 26,
        waveSpeed: 0.55,
      });
    }

    let typed = null;
    if (enableDecorativeEngines && window.Typed && heroTypedRef.current) {
      typed = new window.Typed(heroTypedRef.current, {
        strings: ["learning.", "users.", "analytics.", "content delivery.", "your institution."],
        typeSpeed: 55,
        backSpeed: 30,
        backDelay: 1800,
        loop: true,
        cursorChar: "_",
      });
    }

    if (enableDecorativeEngines && window.VanillaTilt) {
      window.VanillaTilt.init(document.querySelectorAll(".feature-card, .pricing-card"), {
        max: 4,
        speed: 300,
        glare: false,
        scale: 1.01
      });
      const heroCard = document.querySelector(".hero-card");
      if (heroCard) window.VanillaTilt.init(heroCard, { max: 5, glare: false, scale: 1.01 });
    }

    const magneticBtns = document.querySelectorAll(".magnetic");
    const handleMagneticMove = function (e) {
      const rect = this.getBoundingClientRect();
      const x = (e.clientX - rect.left - rect.width / 2) * 0.25;
      const y = (e.clientY - rect.top - rect.height / 2) * 0.25;
      if (gsap) gsap.to(this, { x, y, duration: 0.3, ease: "power2.out" });
    };
    const handleMagneticLeave = function () {
      if (gsap) gsap.to(this, { x: 0, y: 0, duration: 0.5, ease: "elastic.out(1,0.4)" });
    };
    if (enablePointerEffects) {
      magneticBtns.forEach((btn) => {
        btn.addEventListener("mousemove", handleMagneticMove);
        btn.addEventListener("mouseleave", handleMagneticLeave);
      });
    }

    let ctx;
    if (reduceMotion) {
      revealPage();
    } else if (gsap && ScrollTrigger) {
      ctx = gsap.context(() => {
        gsap.timeline()
          .to(".loader-bar", { width: "100%", duration: 1, ease: "power2.inOut" })
          .to(".loader", { opacity: 0, duration: 0.45, ease: "power2.out" })
          .set(".loader", { display: "none" })
          .call(() => window.clearTimeout(loaderFallback));

        ScrollTrigger.create({
          start: "top top",
          end: "max",
          onUpdate: (self) => gsap.to(".progress-bar", { scaleX: self.progress, ease: "none", duration: 0 }),
        });

        // Hero entrance
        gsap.timeline({ delay: 0.2 })
          .from(".hero-eyebrow", { opacity: 0, y: 20, duration: 0.6, ease: "power2.out" })
          .from(".hero-headline", { opacity: 0, y: 40, duration: 0.8, ease: "power3.out" }, "-=0.4")
          .from(".hero-sub", { opacity: 0, y: 30, duration: 0.7, ease: "power3.out" }, "-=0.6")
          .from(".hero-ctas", { opacity: 0, y: 20, duration: 0.6, ease: "power2.out" }, "-=0.5")
          .from(".hero-card-wrap", { opacity: 0, x: 60, duration: 1, ease: "power3.out" }, "-=0.7");

        // Progress bar widths
        document.querySelectorAll('.lr-bar').forEach(bar => {
          gsap.to(bar, { width: bar.style.width || "50%", duration: 1.2, ease: "power2.out", delay: 0.8 });
        });

        gsap.to(".hero-card-wrap", {
          y: -100,
          scrollTrigger: { trigger: "#hero", start: "top top", end: "bottom top", scrub: 1.5 },
        });

        // Feature cards stagger
        gsap.from(".feature-card", {
          opacity: 0, y: 60, duration: 0.8, stagger: 0.1,
          ease: "power3.out",
          scrollTrigger: { trigger: ".features-grid", start: "top 80%" },
        });

        // Step cards stagger
        gsap.from(".step-card", {
          opacity: 0, scale: 0.85, y: 30, duration: 0.7, stagger: 0.2,
          ease: "back.out(1.3)",
          scrollTrigger: { trigger: ".steps-row", start: "top 75%" },
        });

        // Connector draw-in
        gsap.from(".step-connector", {
          scaleX: 0, transformOrigin: "left center", duration: 1.2,
          ease: "power2.inOut",
          scrollTrigger: { trigger: ".steps-row", start: "top 75%" },
        });

        gsap.from(".pricing-card", {
          opacity: 0, y: 80, scale: 0.9, stagger: 0.15, duration: 0.8, ease: "back.out(1.2)",
          scrollTrigger: { trigger: ".pricing-grid", start: "top 80%" },
        });

        gsap.from(".security-card", {
          opacity: 0, y: 40, stagger: 0.1, duration: 0.7, ease: "power3.out",
          scrollTrigger: { trigger: ".security-grid", start: "top 80%" },
        });

        gsap.from(".integration-card", {
          opacity: 0, y: 30, stagger: 0.08, duration: 0.6, ease: "power3.out",
          scrollTrigger: { trigger: ".integrations-grid", start: "top 80%" },
        });

        // CTA section
        gsap.from(".cta-title, .cta-sub", {
          opacity: 0, y: 40, stagger: 0.15, duration: 0.8, ease: "power3.out",
          scrollTrigger: { trigger: "#cta-section", start: "top 80%" },
        });

      });
    }

    return () => {
      if (ctx) ctx.revert();
      clearInterval(pulseInterval);
      document.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("scroll", handleScroll);
      window.clearTimeout(loaderFallback);
      if (mouseRaf) window.cancelAnimationFrame(mouseRaf);
      if (vantaHero) vantaHero.destroy();
      if (vantaCta) vantaCta.destroy();
      if (typed) typed.destroy();
      magneticBtns.forEach((btn) => {
        btn.removeEventListener("mousemove", handleMagneticMove);
        btn.removeEventListener("mouseleave", handleMagneticLeave);
      });
      if (window.ScrollTrigger) window.ScrollTrigger.getAll().forEach((t) => t.kill());
    };
  }, []);

  useEffect(() => {
    if (window.gsap) {
      const target = document.querySelector(".sol-panel.active");
      if (target) {
        window.gsap.fromTo(target, { opacity: 0, x: 20 }, { opacity: 1, x: 0, duration: 0.4 });
      }
    }
  }, [activeTab]);

  useEffect(() => {
    if (window.gsap) {
      window.gsap.fromTo(".integration-card",
        { opacity: 0, y: 15, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: 0.35, stagger: 0.05, ease: "power2.out" }
      );
    }
  }, [activeIntegrationTab]);

  useEffect(() => {
    if (window.gsap) {
      window.gsap.fromTo(".preview-window",
        { opacity: 0, scale: 0.98, y: 10 },
        { opacity: 1, scale: 1, y: 0, duration: 0.45, ease: "power2.out" }
      );
    }
  }, [activePreviewTab]);

  const filteredIntegrations = activeIntegrationTab === "All"
    ? INTEGRATIONS
    : INTEGRATIONS.filter(item => item.category === activeIntegrationTab);

  return (
    <div className="landing-wrapper">
      {/* ── STICKY CTA BANNER ── */}
      <div className={`sticky-cta-banner ${showStickyCTA ? "visible" : ""}`}>
        <div className="sticky-cta-inner">
          <span className="sticky-cta-text">Transform your learning operations with Telite LMS.</span>
          <div className="sticky-cta-actions">
            <button className="btn-sticky-contact magnetic" onClick={() => setShowContactModal(true)}>Book a Demo</button>
            <Link to="/signup" className="btn-sticky-primary magnetic">Get Started Free</Link>
          </div>
        </div>
      </div>

      <div className="cursor" ref={cursorRef}></div>
      <div className="cursor-dot" ref={cursorDotRef}></div>
      <div className="loader">
        <div className="loader-logo">Telite <span>LMS</span></div>
        <div className="loader-bar-wrap"><div className="loader-bar"></div></div>
        <div className="loader-pct">0%</div>
      </div>
      <div className="scroll-progress"><div className="progress-bar"></div></div>

      {/* ── NAVBAR ── */}
      <nav id="lp-nav">
        <Link to="/" className="nav-logo">Telite LMS</Link>
        <ul className="nav-links">
          <li><a href="#features">Features</a></li>
          <li><a href="#solutions">Solutions</a></li>
          <li><a href="#pricing">Pricing</a></li>
          <li><a href="#howitworks">How it works</a></li>
          <li><a href="#cta-section">Contact</a></li>
        </ul>
        <div className="nav-actions">
          <button className="cmd-btn magnetic" onClick={() => setShowCommandPalette(true)} aria-label="Open Command Palette">
            <span>Commands</span><kbd>⌘K</kbd>
          </button>
          <button className="theme-btn magnetic" onClick={toggleTheme} aria-label="Toggle Theme">
            {isDark ? '☀️' : '🌙'}
          </button>
          {dashboardLink ? <Link to={dashboardLink} className="btn-primary magnetic">Go to Dashboard</Link> : <>
            <Link to="/login" className="btn-ghost">Sign in</Link>
            <Link to="/signup" className="btn-primary magnetic">Get started free</Link>
          </>}
        </div>

        {/* Mobile Hamburger Button */}
        <button 
          className={`mobile-menu-btn ${isMobileMenuOpen ? "active" : ""}`} 
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Toggle Navigation Menu"
          aria-expanded={isMobileMenuOpen}
        >
          <span></span>
          <span></span>
          <span></span>
        </button>
      </nav>

      {/* Backdrop blurred Drawer navigation */}
      <div className={`mobile-drawer-overlay ${isMobileMenuOpen ? "active" : ""}`} onClick={() => setIsMobileMenuOpen(false)}></div>
      <div className={`mobile-drawer ${isMobileMenuOpen ? "active" : ""}`}>
        <div className="mobile-drawer-header">
          <Link to="/" className="nav-logo logo-dark" onClick={() => setIsMobileMenuOpen(false)}>Telite LMS</Link>
        </div>
        <ul className="mobile-drawer-links">
          <li><a href="#features" onClick={() => setIsMobileMenuOpen(false)}>Features</a></li>
          <li><a href="#solutions" onClick={() => setIsMobileMenuOpen(false)}>Solutions</a></li>
          <li><a href="#pricing" onClick={() => setIsMobileMenuOpen(false)}>Pricing</a></li>
          <li><a href="#howitworks" onClick={() => setIsMobileMenuOpen(false)}>How it works</a></li>
          <li><a href="#cta-section" onClick={() => setIsMobileMenuOpen(false)}>Contact</a></li>
        </ul>
        <div className="mobile-drawer-actions">
          {dashboardLink ? <Link to={dashboardLink} className="btn-drawer-primary" onClick={() => setIsMobileMenuOpen(false)}>Go to Dashboard</Link> : <>
            <Link to="/login" className="btn-drawer-ghost" onClick={() => setIsMobileMenuOpen(false)}>Sign in</Link>
            <Link to="/signup" className="btn-drawer-primary" onClick={() => setIsMobileMenuOpen(false)}>Get started free</Link>
          </>}
        </div>
      </div>

      {/* ── HERO ── */}
      <section id="hero">
        <div id="hero-bg" ref={vantaHeroRef}></div>
        {/* Decorative gradient orbs */}
        <div className="hero-orb hero-orb--1"></div>
        <div className="hero-orb hero-orb--2"></div>
        <div className="hero-orb hero-orb--3"></div>
        <div className="hero-content">
          <div className="hc-left">
            <div className="hero-eyebrow"><span className="hero-eyebrow-dot"></span>Internal Learning Platform</div>
            <h1 className="hero-headline">
              One platform to manage<br />
              <span className="hero-typed-line"><span id="hero-typed" ref={heroTypedRef}></span></span>
            </h1>
            <p className="hero-sub">Streamline education and training with role-based dashboards, real-time tracking, and seamless LMS integration.</p>
            <div className="hero-ctas">
              <Link to={dashboardLink || "/signup"} className="btn-hero-primary magnetic">{dashboardLink ? "Go to Dashboard" : "Get started free"}</Link>
              <a href="#features" className="btn-hero-ghost magnetic">Explore features</a>
            </div>
            <div className="hero-ticker">
              <span className="ticker-label">AI Insights Live</span>
              <div className="ticker-feed">
                <span>Predictive learning models active...</span>
              </div>
            </div>
          </div>
          <div className="hero-card-wrap">
            <div className="hero-card">
              <div className="hc-header"><span className="hc-dot"></span><span className="hc-title">ATS Admin Dashboard</span><span className="hc-badge">Admin Panel</span></div>
              <div className="hc-metrics">
                <div className="hc-metric"><span className="num">6</span><small>Orgs</small></div>
                <div className="hc-metric"><span className="num">17</span><small>Courses</small></div>
                <div className="hc-metric hl"><span className="num">81%</span><small>Avg Score</small></div>
              </div>
              <div className="hc-learners">
                {[
                  ["Ratan Singh", "68%", ""],
                  ["Priya Seth", "82%", ""],
                  ["Amey Titty", "41%", "warn"],
                  ["Sara Verma", "75%", ""],
                ].map(([name, pct, warn]) => (
                  <div className="lr" key={name}><span className="lr-name">{name}</span><div className="lr-bar-wrap"><div className={`lr-bar ${warn}`} style={{ width: pct }}></div></div><span className="lr-pct">{pct}</span></div>
                ))}
              </div>
              <div className="hc-footer"><span>1 pending enrollment</span><a href="#features">2 at-risk learners →</a></div>
            </div>

            {/* Floating micro-cards */}
            <div className="hero-float-card hero-float--1">
              <svg viewBox="0 0 18 18" fill="none" stroke="#10b981" strokeWidth="2" width="18" height="18"><path d="M4 9l3 3 7-7"/></svg>
              <span>Moodle synced</span>
            </div>
            <div className="hero-float-card hero-float--2">
              <svg viewBox="0 0 18 18" fill="none" stroke="#818cf8" strokeWidth="2" width="18" height="18"><circle cx="9" cy="9" r="7"/><path d="M9 5v4l3 2"/></svg>
              <span>42 active now</span>
            </div>
            <div className="hero-float-card hero-float--3">
              <svg viewBox="0 0 18 18" fill="none" stroke="#f59e0b" strokeWidth="2" width="18" height="18"><path d="M9 2l2 4 5 1-4 3 1 5-4-2-4 2 1-5-4-3 5-1z"/></svg>
              <span>AI analyzing</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── TRUST LOGOS ── */}
      <section className="trust-section">
        <span className="trust-eyebrow">Trusted by 200+ institutions & enterprises globally</span>
        <div className="trust-marquee-container">
          <div className="trust-marquee-track">
            {[...TRUST_LOGOS, ...TRUST_LOGOS].map((logo, idx) => (
              <div className="trust-logo-card" key={`${logo.name}-${idx}`}>
                {logo.svg}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section id="features">
        <div className="inner">
          <div className="features-header">
            <span className="section-eyebrow">Everything you need</span>
            <h2 className="section-title">Built for modern learning<br />operations</h2>
            <p className="section-sub">A complete toolkit for admins, instructors, and learners.</p>
          </div>
          <div className="features-grid">{FEATURES.map((f) => <FeatureCard key={f.id} f={f} />)}</div>
        </div>
      </section>

      {/* ── AI SHOWCASE SECTION ── */}
      <section id="ai-showcase">
        <div className="inner ai-showcase-layout">
          <div className="ai-showcase-left">
            <span className="section-eyebrow ai-glow-text">AI Diagnostics</span>
            <h2 className="section-title text-light">Predictive learning<br />intelligence</h2>
            <p className="section-sub text-light-muted">Telite doesn't just record scores; our proactive machine learning layer analyzes cognitive habits, identifies fatigue patterns, and alerts instructors before a learner falls behind.</p>
            
            <div className="ai-features-list">
              <div className="ai-feat-item">
                <div className="ai-feat-dot"></div>
                <div>
                  <h4>Cognitive Fatigue Detection</h4>
                  <p>Monitors action-delays, navigation pacing, and session intervals to map individual learning curves.</p>
                </div>
              </div>
              <div className="ai-feat-item">
                <div className="ai-feat-dot"></div>
                <div>
                  <h4>Automated Risk Vector Triggers</h4>
                  <p>Instantly flags at-risk profiles and suggests tailored remedial pathways with zero administrative overhead.</p>
                </div>
              </div>
            </div>
          </div>
          <div className="ai-showcase-right">
            <div className="ai-interactive-card">
              <div className="ai-card-header">
                <span className="ai-status-pulse"></span>
                <span className="ai-card-title">Cognitive Diagnostic Panel</span>
                <span className="ai-card-tag">Active Analysis</span>
              </div>
              <div className="ai-risk-profile">
                <div className="ai-profile-main">
                  <div className="ai-avatar-placeholder">SK</div>
                  <div>
                    <div className="ai-profile-name">Shreyas Kulkarni</div>
                    <div className="ai-profile-meta">Category: Advanced Cryptography</div>
                  </div>
                </div>
                <div className="ai-risk-badge high-risk">High Risk Vector</div>
              </div>
              <div className="ai-diagnostics-metrics">
                <div className="ai-diag-metric">
                  <span className="ai-diag-lbl">Velocity Profile</span>
                  <span className="ai-diag-val warning-val">-24% drop-off</span>
                </div>
                <div className="ai-diag-metric">
                  <span className="ai-diag-lbl">Concept Retention</span>
                  <span className="ai-diag-val">82% accuracy</span>
                </div>
                <div className="ai-diag-metric">
                  <span className="ai-diag-lbl">Cognitive Load</span>
                  <span className="ai-diag-val danger-val">Fatigue detected</span>
                </div>
              </div>
              <div className="ai-card-remedial">
                <div className="ai-remedial-title">AI Suggested Remedial Action</div>
                <p className="ai-remedial-desc">Insert micro-conceptual recap quiz covering "Symmetric Cipher Blocks" and delay Module 4 by 48 hours.</p>
                <button className="btn-ai-action">Approve Path</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SOLUTIONS ── */}
      <section id="solutions">
        <div className="inner">
          <span className="section-eyebrow">Solutions</span>
          <h2 className="section-title">Built for your context</h2>
          <p className="section-sub">Whether managing students across departments or training employees at scale.</p>
          <div className="solutions-grid">
            <div className="sol-left">
              <div className="sol-tabs">
                <button className={`sol-tab magnetic ${activeTab === "college" ? "active" : ""}`} onClick={() => setActiveTab("college")}>For Colleges</button>
                <button className={`sol-tab magnetic ${activeTab === "company" ? "active" : ""}`} onClick={() => setActiveTab("company")}>For Companies</button>
              </div>
              <div className={`sol-panel ${activeTab === "college" ? "active" : ""}`}>
                <h3 className="sol-headline">Academic learning management</h3>
                <ul className="sol-checklist">
                  {["Manage students, courses, and departments", "Academic analytics and attendance tracking", "Role-based access per faculty and staff", "Bulk enrollment and verification tools", "Moodle integration for existing systems"].map((item) => <li key={item}><span className="check-icon"><svg viewBox="0 0 16 16" fill="none" stroke="#10b981" strokeWidth="2"><path d="M4 8l3 3 5-6"/></svg></span>{item}</li>)}
                </ul>
              </div>
              <div className={`sol-panel ${activeTab === "company" ? "active" : ""}`}>
                <h3 className="sol-headline">Employee training and upskilling</h3>
                <ul className="sol-checklist">
                  {["Onboarding and compliance training paths", "Skill tracking and attendance management", "Team-level performance dashboards", "Domain-restricted signup and access control", "Export reports as CSV or PDF"].map((item) => <li key={item}><span className="check-icon"><svg viewBox="0 0 16 16" fill="none" stroke="#10b981" strokeWidth="2"><path d="M4 8l3 3 5-6"/></svg></span>{item}</li>)}
                </ul>
              </div>
            </div>
            <div className="sol-visual">
              <div className="sol-stats">
                <div className="sol-stat accent"><div className="big"><CountUp target={1284} /></div><div className="lbl">Organizations</div></div>
                <div className="sol-stat"><div className="big"><CountUp target={2.4} decimals={1} suffix="M" useSeparator={false} /></div><div className="lbl">Learners</div></div>
                <div className="sol-stat"><div className="big"><CountUp target={98.2} decimals={1} suffix="%" useSeparator={false} /></div><div className="lbl">Sync Rate</div></div>
                <div className="sol-stat accent"><div className="big"><CountUp target={42} suffix="min" /></div><div className="lbl">Avg Session</div></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── PRODUCT PREVIEW & LIVE ANALYTICS SHOWCASE ── */}
      <section id="product-preview">
        <div className="inner">
          <div className="preview-header">
            <span className="section-eyebrow">Interactive Sandbox</span>
            <h2 className="section-title">See Telite LMS in Action</h2>
            <p className="section-sub">Experience our lightning-fast analytical layers, operational queues, and curriculum building tools.</p>
          </div>

          <div className="preview-container">
            <div className="preview-tabs">
              <button 
                className={`preview-tab magnetic ${activePreviewTab === "analytics" ? "active" : ""}`}
                onClick={() => setActivePreviewTab("analytics")}
              >
                Workspace Analytics
              </button>
              <button 
                className={`preview-tab magnetic ${activePreviewTab === "operations" ? "active" : ""}`}
                onClick={() => setActivePreviewTab("operations")}
              >
                Admin Operations
              </button>
              <button 
                className={`preview-tab magnetic ${activePreviewTab === "builder" ? "active" : ""}`}
                onClick={() => setActivePreviewTab("builder")}
              >
                Course Builder
              </button>
            </div>

            <div className="preview-window">
              <div className="window-header">
                <div className="window-dots">
                  <span className="dot red"></span>
                  <span className="dot yellow"></span>
                  <span className="dot green"></span>
                </div>
                <div className="window-address">https://app.telite.edu/dashboard/{activePreviewTab}</div>
              </div>
              <div className="window-body">
                {activePreviewTab === "analytics" && (
                  <div className="preview-pane-analytics">
                    <div className="pane-sidebar">
                      <div className="sidebar-metric">
                        <span className="label">Completion Index</span>
                        <h4 className="value">84.5%</h4>
                        <span className="subtext green">+3.2% vs Moodle raw</span>
                      </div>
                      <div className="sidebar-metric">
                        <span className="label">Active Study Pacing</span>
                        <h4 className="value">4.8 hrs</h4>
                        <span className="subtext">Daily average session</span>
                      </div>
                      <div className="sidebar-metric">
                        <span className="label">Satisfaction Score</span>
                        <h4 className="value">4.92/5</h4>
                        <span className="subtext green">99.8% positive feedback</span>
                      </div>
                    </div>
                    <div className="pane-chart-container">
                      <div className="pane-chart-header">
                        <h4>Cohort Progression Trends</h4>
                        <p>Real-time analytics syncing directly from institutional webhooks.</p>
                      </div>
                      <div className="chart-canvas-wrap">
                        <Line data={PREVIEW_CHART_DATA} options={PREVIEW_CHART_OPTIONS} />
                      </div>
                    </div>
                  </div>
                )}

                {activePreviewTab === "operations" && (
                  <div className="preview-pane-operations">
                    <div className="pane-header">
                      <h4>SuperAdmin Enrollment Approvals Queue</h4>
                      <p>Filter, verify, and approve domain-restricted student enrollments in real time.</p>
                    </div>
                    <div className="approvals-list">
                      {approvals.map((app) => (
                        <div className={`approval-row ${app.status.toLowerCase()}`} key={app.id}>
                          <div className="app-info">
                            <span className="app-name">{app.name}</span>
                            <span className="app-org">{app.org}</span>
                            <span className="app-course">{app.course}</span>
                          </div>
                          <div className="app-actions">
                            {app.status === "Pending" ? (
                              <>
                                <button className="btn-approve magnetic" onClick={() => handleApprove(app.id)}>Approve</button>
                                <button className="btn-reject magnetic" onClick={() => handleReject(app.id)}>Reject</button>
                              </>
                            ) : (
                              <span className={`status-pill ${app.status.toLowerCase()}`}>{app.status}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="pane-footer-text">
                      <span>{approvals.filter(a => a.status === "Pending").length} pending verification checkouts in current queue</span>
                    </div>
                  </div>
                )}

                {activePreviewTab === "builder" && (
                  <div className="preview-pane-builder">
                    <div className="pane-header">
                      <h4>Course Curriculum Composer</h4>
                      <p>Toggle modular course chunks to dynamically adjust syllabus weight and pacing paths.</p>
                    </div>
                    <div className="modules-list">
                      {modules.map((m) => (
                        <div className={`module-row ${m.active ? "active" : ""}`} key={m.id}>
                          <div className="module-info">
                            <span className="module-title">{m.title}</span>
                            <span className="module-duration">{m.duration}</span>
                          </div>
                          <div className="module-action">
                            <button className={`toggle-btn-switch ${m.active ? "on" : "off"}`} onClick={() => toggleModule(m.id)}>
                              <span className="switch-dot"></span>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="builder-summary">
                      <div className="summary-item">
                        <span className="label">Active Modules</span>
                        <span className="val">{modules.filter(m => m.active).length} / {modules.length}</span>
                      </div>
                      <div className="summary-item">
                        <span className="label">Total Syllabus Duration</span>
                        <span className="val">{modules.filter(m => m.active).reduce((sum, m) => sum + parseInt(m.duration), 0)} Hours</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECURITY SECTION ── */}
      <section id="security-trust">
        <div className="inner">
          <div className="security-header">
            <span className="section-eyebrow">Enterprise Security</span>
            <h2 className="section-title">Guardians of your learning data</h2>
            <p className="section-sub">Telite is engineered with state-of-the-art security compliance to protect institutional privacy and intellectual assets.</p>
          </div>
          <div className="security-grid">
            <div className="security-card">
              <div className="sec-icon-wrap">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              </div>
              <h3 className="sec-title">Military-Grade Encryption</h3>
              <p className="sec-desc">End-to-end cryptographic shielding utilizing AES-256 for data-at-rest and TLS 1.3 for active operations in-transit.</p>
            </div>
            <div className="security-card">
              <div className="sec-icon-wrap">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>
              </div>
              <h3 className="sec-title">Row-Level Tenancy Security</h3>
              <p className="sec-desc">Strict, cryptographically isolated boundary policies running on the database-level to guarantee absolute data privacy.</p>
            </div>
            <div className="security-card">
              <div className="sec-icon-wrap">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              </div>
              <h3 className="sec-title">Continuous Audit Logs</h3>
              <p className="sec-desc">Immutable audit trails recording credential configurations, role promotions, access vectors, and administrative workflows.</p>
            </div>
            <div className="security-card">
              <div className="sec-icon-wrap">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/></svg>
              </div>
              <h3 className="sec-title">GDPR & ISO Readiness</h3>
              <p className="sec-desc">Direct compliance frameworks engineered aligned with SOC 2 Type II, ISO 27001, and global GDPR residency mandates.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── INTEGRATION ECOSYSTEM Grid ── */}
      <section id="integrations">
        <div className="inner">
          <div className="integrations-header">
            <span className="section-eyebrow">Ecosystem</span>
            <h2 className="section-title">Seamless Integrations</h2>
            <p className="section-sub">Connect your existing workflows, LMS platforms, and identity providers with one click.</p>
          </div>
          <div className="integrations-tabs-wrapper">
            <div className="integrations-tabs">
              {["All", "LMS", "Communication", "Payments", "Enterprise"].map((cat) => (
                <button
                  key={cat}
                  className={`integration-tab magnetic ${activeIntegrationTab === cat ? "active" : ""}`}
                  onClick={() => setActiveIntegrationTab(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
          <div className="integrations-grid">
            {filteredIntegrations.map((item) => (
              <div className="integration-card" key={item.name}>
                <div className="int-card-header">
                  <div className="int-logo-wrapper">
                    {item.svg}
                  </div>
                  <span className={`status-badge ${item.status.toLowerCase().replace(" ", "-")}`}>
                    {item.status}
                  </span>
                </div>
                <h3 className="int-name">{item.name}</h3>
                <span className="int-category">{item.category}</span>
                <p className="int-desc">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="howitworks">
        <div className="inner">
          <div className="steps-header">
            <span className="section-eyebrow">How it works</span>
            <h2 className="section-title">Up and running in three steps</h2>
            <p className="section-sub">No complex setup. Your team can be learning within hours.</p>
          </div>
          <div className="steps-row">
            <div className="step-connector"></div>
            {[
              ["1", "Create your workspace", "Set up your organisation, configure allowed domains, and invite your first admins. Under five minutes."],
              ["2", "Add users and courses", "Bulk import learners, create learning categories, publish courses with modules, and assign tasks."],
              ["3", "Track and optimise", "Monitor real-time progress, PAL scores, and completion rates. Export reports and act on at-risk alerts."],
            ].map(([num, title, desc]) => (
              <div className="step-card" key={num}>
                <div className="step-num">{num}</div>
                <div className="step-card-body">
                  <h3 className="step-title">{title}</h3>
                  <p className="step-desc">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ── */}
      <section id="testimonials">
        <div className="header-wrap"><span className="section-eyebrow">Testimonials</span><h2 className="section-title">Trusted by learning teams</h2></div>
        <div className="marquee-outer"><div className="marquee-track">{[...TESTIMONIALS, ...TESTIMONIALS].map((t, idx) => <div className="testi-card" key={`${t.name}-${idx}`}><div className="stars">{Array.from({ length: t.stars }).map((_, i) => <span key={i} className="star">★</span>)}</div><p className="testi-quote">"{t.quote}"</p><div className="testi-author"><div className="testi-avatar">{t.name.split(" ").map((n) => n[0]).join("")}</div><div><div className="testi-name">{t.name}</div><div className="testi-role">{t.role}</div></div></div></div>)}</div></div>
      </section>

      {/* ── PRICING ── */}
      <section id="pricing">
        <div className="inner">
          <div className="pricing-header">
            <span className="section-eyebrow">Pricing</span>
            <h2 className="section-title">Simple, transparent pricing</h2>
            <div className="pricing-trust-line">Trusted by 120+ institutions globally</div>
            <p className="section-sub">Start free. Scale as you grow. No hidden fees.</p>
          </div>
          <div className="pricing-toggle">
            <span className={`toggle-label ${!isAnnual ? "active" : ""}`} onClick={() => handleToggle()}>Monthly</span>
            <div className={`toggle-switch ${isAnnual ? "annual" : ""}`} onClick={handleToggle} role="switch" aria-checked={isAnnual} aria-label="Toggle annual pricing"></div>
            <span className={`toggle-label ${isAnnual ? "active" : ""}`} onClick={() => handleToggle()}>Annually</span>
            <span className="toggle-badge">Save 20%</span>
          </div>
          <div className="pricing-grid">
            {PLANS.map((p) => (
              <div
                key={p.name}
                className={`pricing-card ${p.highlight ? "pro" : ""} ${selectedPlan === p.name ? "selected" : ""}`}
                onClick={() => setSelectedPlan(p.name)}
                role="button"
                tabIndex={0}
                aria-label={`Select ${p.name} plan`}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setSelectedPlan(p.name); }}
              >
                {p.highlight && <span className="pro-badge">Most popular</span>}
                <div className="plan-name">{p.name}</div>
                <div className="plan-tag">{p.tag}</div>
                <div
                  className="plan-price price-number"
                  ref={(el) => { priceRefsMap.current[p.name] = el; }}
                >
                  {isAnnual ? p.price.annual : p.price.monthly}
                </div>
                <div className="plan-period">{isAnnual && p.name === "Pro" ? "per month, billed annually" : p.period}</div>
                <ul className="plan-features">
                  {p.features.map((feature) => (
                    <li key={feature}>
                      <span className="pf-check"><svg viewBox="0 0 16 16" fill="none" stroke="#10b981" strokeWidth="2"><path d="M4 8l3 3 5-6"/></svg></span>{feature}
                    </li>
                  ))}
                </ul>
                <Link
                  to={dashboardLink || (p.price.monthly === "Custom" ? "#" : "/signup")}
                  className={`btn-plan magnetic ${p.highlight ? "btn-plan-white" : p.price.monthly === "Custom" ? "btn-plan-ghost" : "btn-plan-outline"}`}
                  onClick={(e) => {
                    if (p.price.monthly === "Custom") {
                      e.preventDefault();
                      e.stopPropagation();
                      setShowContactModal(true);
                    } else {
                      e.stopPropagation();
                    }
                  }}
                >
                  {dashboardLink ? "Go to Dashboard" : p.price.monthly === "Custom" ? "Contact Sales" : "Get started"}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ SECTION ── */}
      <section id="faq">
        <div className="inner">
          <div className="faq-header">
            <span className="section-eyebrow">FAQ</span>
            <h2 className="section-title">Frequently asked questions</h2>
            <p className="section-sub">Have questions about Telite LMS? Find quick answers right here.</p>
          </div>
          <div className="faq-list">
            {FAQS.map((faq, index) => (
              <FAQItem key={index} item={faq} />
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ── */}
      <section id="cta-section">
        <div id="cta-vanta" ref={vantaCtaRef}></div>
        <div className="cta-content">
          <h2 className="cta-title">Ready to modernise your<br />learning operations?</h2>
          <p className="cta-sub">Join thousands of colleges and companies already using Telite LMS.</p>
          <div className="cta-btns">
            <Link to={dashboardLink || "/signup"} className="btn-cta-white magnetic">{dashboardLink ? "Go to Dashboard" : "Get started free"}</Link>
            <a href="#features" className="btn-cta-outline magnetic">Explore features</a>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer>
        <div className="footer-grid">
          <div>
            <span className="footer-brand-name">Telite LMS</span>
            <p className="footer-brand-desc">Role-driven learning operations for colleges, companies, and training institutes.</p>
            <div className="footer-social">
              <a href="#" aria-label="Twitter / X">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4l11.733 16h4.267l-11.733-16zM4 20l6.768-6.768M20 4l-6.768 6.768"/></svg>
              </a>
              <a href="#" aria-label="LinkedIn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-4 0v7h-4v-7a6 6 0 016-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>
              </a>
              <a href="#" aria-label="GitHub">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22"/></svg>
              </a>
              <a href="mailto:support@telitesystems.com" aria-label="Email">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>
              </a>
            </div>
            <div className="footer-newsletter">
              <h5 className="newsletter-title">Subscribe to updates</h5>
              {newsletterSuccess ? (
                <div className="newsletter-success-msg">Thanks! You are subscribed.</div>
              ) : (
                <form onSubmit={handleNewsletterSubmit} className="newsletter-form">
                  <input
                    type="email"
                    placeholder="Enter your email"
                    required
                    value={newsletterEmail}
                    onChange={(e) => setNewsletterEmail(e.target.value)}
                    aria-label="Email Address for newsletter"
                  />
                  <button type="submit" className="btn-newsletter-submit" aria-label="Subscribe">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                      <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                  </button>
                </form>
              )}
            </div>
          </div>
          <div>
            <h5 className="footer-col-title">Product</h5>
            <ul className="footer-links">
              <li><a href="#features">Features</a></li>
              <li><a href="#pricing">Pricing</a></li>
              <li><a href="#">Integrations</a></li>
              <li><a href="#">Changelog</a></li>
              <li><a href="#">Roadmap</a></li>
            </ul>
          </div>
          <div>
            <h5 className="footer-col-title">Company</h5>
            <ul className="footer-links">
              <li><a href="#">About us</a></li>
              <li><a href="#">Blog</a></li>
              <li><a href="#">Careers</a></li>
              <li><a href="#">Press</a></li>
              <li><a href="#">Security</a></li>
            </ul>
          </div>
          <div>
            <h5 className="footer-col-title">Support</h5>
            <ul className="footer-links">
              <li><a href="#">Documentation</a></li>
              <li><a href="#">API Docs</a></li>
              <li><a href="#">Help center</a></li>
              <li><a href="#">Status</a></li>
              <li><a href="mailto:support@telitesystems.com">Contact</a></li>
            </ul>
          </div>
          <div>
            <h5 className="footer-col-title">Legal</h5>
            <ul className="footer-links">
              <li><a href="#">Privacy Policy</a></li>
              <li><a href="#">Terms of Service</a></li>
              <li><a href="#">Cookie Policy</a></li>
              <li><a href="#">GDPR Compliance</a></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© 2026 Telite Systems. All rights reserved.</span>
        </div>
      </footer>

      {/* ── CONTACT/DEMO MODAL ── */}
      {showContactModal && (
        <div className="modal-overlay" onClick={() => setShowContactModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowContactModal(false)} aria-label="Close modal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
            {contactSuccess ? (
              <div className="modal-success-state">
                <div className="success-checkmark-wrapper">
                  <svg className="success-checkmark" viewBox="0 0 52 52">
                    <circle className="success-checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
                    <path className="success-checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                  </svg>
                </div>
                <h3>Request Submitted!</h3>
                <p>Our learning operations specialists will reach out to you within 24 hours to schedule a custom walkthrough.</p>
              </div>
            ) : (
              <>
                <h3>Book a Live Demo</h3>
                <p className="modal-subtitle">Experience how Telite LMS orchestrates complex learning ecosystems.</p>
                <form onSubmit={handleContactSubmit}>
                  {contactError && <div className="form-error-banner">{contactError}</div>}
                  <div className="form-group">
                    <label htmlFor="modal-name">Full Name</label>
                    <input
                      id="modal-name"
                      type="text"
                      placeholder="E.g., Vikram Pillai"
                      required
                      value={contactForm.name}
                      onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="modal-email">Work Email</label>
                    <input
                      id="modal-email"
                      type="email"
                      placeholder="E.g., vikram@edubridge.in"
                      required
                      value={contactForm.email}
                      onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="modal-org">Organization</label>
                    <input
                      id="modal-org"
                      type="text"
                      placeholder="E.g., EduBridge Learning"
                      required
                      value={contactForm.org}
                      onChange={(e) => setContactForm({ ...contactForm, org: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="modal-type">Organization Type</label>
                    <select
                      id="modal-type"
                      value={contactForm.type}
                      onChange={(e) => setContactForm({ ...contactForm, type: e.target.value })}
                    >
                      <option>College / University</option>
                      <option>Corporate Training</option>
                      <option>Individual Instructor</option>
                      <option>Government Body</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="modal-msg">How can we help?</label>
                    <textarea
                      id="modal-msg"
                      placeholder="Syllabus sync needs, learner limits, etc."
                      value={contactForm.msg}
                      onChange={(e) => setContactForm({ ...contactForm, msg: e.target.value })}
                    />
                  </div>
                  <button type="submit" className="btn-modal-submit magnetic">Schedule My Demo</button>
                </form>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── SUPPORT WIDGET ── */}
      <div className="support-widget-container">
        <button 
          className={`support-widget-badge magnetic ${showSupportWidget ? "active" : ""}`}
          onClick={() => setShowSupportWidget(!showSupportWidget)}
          aria-label="Toggle Support Options"
          aria-expanded={showSupportWidget}
        >
          {showSupportWidget ? (
            <svg className="widget-close-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          ) : (
            <svg className="widget-chat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          )}
        </button>
        
        {showSupportWidget && (
          <div className="support-widget-panel">
            <div className="widget-panel-header">
              <h4>Telite Support Hub</h4>
              <p>How can we assist you today?</p>
            </div>
            <div className="widget-panel-body">
              <a href="#faq" className="widget-link-item" onClick={() => setShowSupportWidget(false)}>
                <div className="widget-item-icon">❓</div>
                <div className="widget-item-content">
                  <h5>Read FAQs</h5>
                  <p>Quick answers to common queries</p>
                </div>
              </a>
              <a href="mailto:support@telitesystems.com" className="widget-link-item">
                <div className="widget-item-icon">📧</div>
                <div className="widget-item-content">
                  <h5>Email Support</h5>
                  <p>Get a response in under 2 hours</p>
                </div>
              </a>
              <a href="#" className="widget-link-item" onClick={(e) => { e.preventDefault(); setShowContactModal(true); setShowSupportWidget(false); }}>
                <div className="widget-item-icon">📅</div>
                <div className="widget-item-content">
                  <h5>Request Call</h5>
                  <p>Schedule a quick phone walkthrough</p>
                </div>
              </a>
            </div>
            <div className="widget-panel-footer">
              <span className="status-indicator online"></span>
              <span className="footer-status-text">Operations team online</span>
            </div>
          </div>
        )}
      </div>

      {/* ── COMMAND PALETTE ── */}
      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
        context={{ setShowContactModal, toggleTheme }}
      />
    </div>
  );
}
