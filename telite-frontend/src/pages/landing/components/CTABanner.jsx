import React from 'react';
import { Link } from 'react-router-dom';

export default function CTABanner({ dashboardLink }) {
  return (
    <section id="cta-section">
      <div id="cta-vanta" />
      <div className="cta-content">
        <h2 className="cta-title">Ready to modernise your<br />learning operations?</h2>
        <p className="cta-sub">Join thousands of colleges and companies already using Telite LMS.</p>
        <div className="cta-btns">
          <Link to={dashboardLink || '/login'} className="btn-cta-white magnetic">{dashboardLink ? 'Go to Dashboard' : 'Get started free'}</Link>
          <a href="#features" className="btn-cta-outline magnetic">Explore features</a>
        </div>
      </div>
    </section>
  );
}
