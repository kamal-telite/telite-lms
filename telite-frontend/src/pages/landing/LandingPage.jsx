import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getDefaultRoute } from "../../context/session";
import { useTheme } from "../../providers/ThemeProvider";
import CommandPalette from "./components/CommandPalette";
import LandingHeader from "./components/LandingHeader";
import HeroSection from "./components/HeroSection";
import TrustLogosSection from "./components/TrustLogosSection";
import FeaturesSection from "./components/FeaturesSection";
import AIShowcaseSection from "./components/AIShowcaseSection";
import SolutionsSection from "./components/SolutionsSection";
import ProductPreview from "./components/ProductPreview";
import SecuritySection from "./components/SecuritySection";
import IntegrationsSection from "./components/IntegrationsSection";
import HowItWorksSection from "./components/HowItWorksSection";
import TestimonialsSection from "./components/TestimonialsSection";
import Pricing from "./components/Pricing";
import FAQSection from "./components/FAQSection";
import CTABanner from "./components/CTABanner";
import LandingFooter from "./components/LandingFooter";
import ContactModal from "./components/ContactModal";
import SupportWidget from "./components/SupportWidget";
import "../../styles/landing.css";
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
import { PLANS } from "./constants/plans";

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

// Chart registration remains in LandingPage so nested landing sections using react-chartjs-2 can render cleanly.

export default function LandingPage({ session }) {
  const dashboardLink = session?.user ? getDefaultRoute(session.user) : null;
  const [isAnnual, setIsAnnual] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("Pro");
  const [activeTab, setActiveTab] = useState("college");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const { resolvedTheme, toggleTheme } = useTheme();
  const vantaHeroRef = useRef(null);
  const vantaCtaRef = useRef(null);
  const heroTypedRef = useRef(null);
  const priceRefsMap = useRef({});

  // Phase 3 states
  const [activeIntegrationTab, setActiveIntegrationTab] = useState("All");
  const [activePreviewTab, setActivePreviewTab] = useState("analytics");
  const [showContactModal, setShowContactModal] = useState(false);
  const [contactForm, setContactForm] = useState({ name: "", email: "", org: "", type: "College / University", msg: "" });
  const [contactError, setContactError] = useState("");
  const [contactSuccess, setContactSuccess] = useState(false);
  const [showSupportWidget, setShowSupportWidget] = useState(false);
  const [newsletterEmail, setNewsletterEmail] = useState("");
  const [newsletterSuccess, setNewsletterSuccess] = useState(false);

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

  return (
    <div className="landing-wrapper">
      <div className="loader">
        <div className="loader-logo">Telite <span>LMS</span></div>
        <div className="loader-bar-wrap"><div className="loader-bar"></div></div>
        <div className="loader-pct">0%</div>
      </div>
      <div className="scroll-progress"><div className="progress-bar"></div></div>

      <LandingHeader
        dashboardLink={dashboardLink}
        resolvedTheme={resolvedTheme}
        toggleTheme={toggleTheme}
        onCommandToggle={() => setShowCommandPalette(true)}
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />
      <HeroSection dashboardLink={dashboardLink} vantaHeroRef={vantaHeroRef} heroTypedRef={heroTypedRef} />
      <TrustLogosSection />
      <FeaturesSection />
      <AIShowcaseSection />
      <SolutionsSection activeTab={activeTab} setActiveTab={setActiveTab} />
      <ProductPreview
        activePreviewTab={activePreviewTab}
        setActivePreviewTab={setActivePreviewTab}
        approvals={approvals}
        handleApprove={handleApprove}
        handleReject={handleReject}
        modules={modules}
        toggleModule={toggleModule}
      />
      <SecuritySection />
      <IntegrationsSection activeIntegrationTab={activeIntegrationTab} setActiveIntegrationTab={setActiveIntegrationTab} />
      <HowItWorksSection />
      <TestimonialsSection />
      <Pricing
        dashboardLink={dashboardLink}
        isAnnual={isAnnual}
        selectedPlan={selectedPlan}
        setSelectedPlan={setSelectedPlan}
        handleToggle={handleToggle}
        plans={PLANS}
        onContactSales={() => setShowContactModal(true)}
      />
      <FAQSection />
      <CTABanner dashboardLink={dashboardLink} />
      <LandingFooter
        dashboardLink={dashboardLink}
        newsletterEmail={newsletterEmail}
        newsletterSuccess={newsletterSuccess}
        setNewsletterEmail={setNewsletterEmail}
        handleNewsletterSubmit={handleNewsletterSubmit}
      />

      <ContactModal
        isOpen={showContactModal}
        onClose={() => setShowContactModal(false)}
        contactForm={contactForm}
        setContactForm={setContactForm}
        contactError={contactError}
        contactSuccess={contactSuccess}
        handleContactSubmit={handleContactSubmit}
      />

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
        <SupportWidget isOpen={showSupportWidget} onClose={() => setShowSupportWidget(false)} />
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
