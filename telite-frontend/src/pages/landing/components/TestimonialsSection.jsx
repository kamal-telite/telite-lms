import React from 'react';
import { TESTIMONIALS } from '../constants/testimonials';

export default function TestimonialsSection() {
  return (
    <section id="testimonials">
      <div className="header-wrap">
        <span className="section-eyebrow">Testimonials</span>
        <h2 className="section-title">Trusted by learning teams</h2>
      </div>
      <div className="marquee-outer">
        <div className="marquee-track">
          {[...TESTIMONIALS, ...TESTIMONIALS].map((t, idx) => (
            <div className="testi-card" key={`${t.name}-${idx}`}>
              <div className="stars">{Array.from({ length: t.stars }).map((_, i) => (<span key={i} className="star">★</span>))}</div>
              <p className="testi-quote">&quot;{t.quote}&quot;</p>
              <div className="testi-author">
                <div className="testi-avatar">{t.name.split(' ').map((n) => n[0]).join('')}</div>
                <div>
                  <div className="testi-name">{t.name}</div>
                  <div className="testi-role">{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
