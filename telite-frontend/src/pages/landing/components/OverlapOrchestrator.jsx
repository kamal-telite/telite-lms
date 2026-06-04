import React, { useEffect, useRef } from "react";
import "../../../styles/landing-sections/overlap.css";

/**
 * OverlapOrchestrator manages Layer 2: Structural Overlaps.
 * It uses GSAP ScrollTrigger to bridge content transitions cinematically.
 */
export default function OverlapOrchestrator() {
  const orchestratorRef = useRef(null);

  useEffect(() => {
    const gsap = window.gsap;
    const ScrollTrigger = window.ScrollTrigger;
    if (!gsap || !ScrollTrigger) return;

    const ctx = gsap.context(() => {
      // 1. Hero -> Trust
      gsap.to(".overlap-hero-trust", {
        opacity: 1, y: 0,
        scrollTrigger: { trigger: "#hero", start: "bottom bottom", toggleActions: "play reverse play reverse", scrub: true }
      });
      gsap.to(".overlap-hero-trust .glass-shard", {
        y: -100, rotation: 5,
        scrollTrigger: { trigger: "#hero", start: "bottom bottom", end: "bottom top", scrub: 1 }
      });

      // 2. AI -> Analytics
      gsap.to(".overlap-ai-analytics", {
        opacity: 1, y: 0,
        scrollTrigger: { trigger: "#ai-showcase", start: "bottom bottom", toggleActions: "play reverse play reverse", scrub: true }
      });
      gsap.fromTo(".overlap-ai-analytics .neural-line", 
        { strokeDashoffset: 1000 },
        { strokeDashoffset: 0, scrollTrigger: { trigger: "#ai-showcase", start: "bottom bottom", end: "bottom center", scrub: 1.5 } }
      );

      // 3. Testimonials -> Pricing
      gsap.to(".overlap-testi-pricing", {
        opacity: 1, y: 0,
        scrollTrigger: { trigger: "#testimonials", start: "bottom bottom", toggleActions: "play reverse play reverse", scrub: true }
      });
      gsap.to(".overlap-testi-pricing .glow-orb", {
        y: -150, opacity: 0.4, scale: 1.2,
        scrollTrigger: { trigger: "#testimonials", start: "bottom bottom", end: "bottom top", scrub: 2 }
      });
    }, orchestratorRef);

    return () => ctx.revert();
  }, []);

  return (
    <div className="overlap-orchestrator" ref={orchestratorRef} aria-hidden="true">
      {/* 1. Hero -> Trust Overlap */}
      <div className="overlap-region overlap-hero-trust" style={{ position: 'fixed', bottom: '10%', opacity: 0 }}>
        <div className="glass-shard shard-1">
          <div className="shard-inner">
            <span className="shard-val">98%</span>
            <span className="shard-lbl">Retention</span>
          </div>
        </div>
        <div className="glass-shard shard-2">
          <div className="shard-inner">
            <span className="shard-val">+2.4k</span>
            <span className="shard-lbl">Active Users</span>
          </div>
        </div>
      </div>

      {/* 2. AI -> Analytics Overlap */}
      <div className="overlap-region overlap-ai-analytics" style={{ position: 'fixed', bottom: '10%', opacity: 0 }}>
        <svg className="neural-connector" viewBox="0 0 100 300" preserveAspectRatio="none">
          <path className="neural-line" d="M50,0 C50,100 20,200 50,300" fill="none" stroke="url(#grad-neural)" strokeWidth="0.8" strokeDasharray="1000" />
          <defs>
            <linearGradient id="grad-neural" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="var(--primary-light)" stopOpacity="0" />
              <stop offset="50%" stopColor="var(--primary-light)" stopOpacity="0.4" />
              <stop offset="100%" stopColor="var(--primary-light)" stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* 3. Testimonials -> Pricing Overlap */}
      <div className="overlap-region overlap-testi-pricing" style={{ position: 'fixed', bottom: '10%', opacity: 0 }}>
        <div className="glow-orb"></div>
        <div className="trust-drift">
          <span className="trust-badge">4.9/5 Rating</span>
          <span className="trust-badge">SOC2 Ready</span>
        </div>
      </div>
    </div>
  );
}
