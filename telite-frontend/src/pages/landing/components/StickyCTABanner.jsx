import React from 'react';
import { Link } from 'react-router-dom';

export default function StickyCTABanner({ visible, onContactClick }) {
  return (
    <div className={`sticky-cta-banner ${visible ? 'visible' : ''}`}>
      <div className="sticky-cta-inner">
        <span className="sticky-cta-text">Transform your learning operations with Telite LMS.</span>
        <div className="sticky-cta-actions">
          <button className="btn-sticky-contact magnetic" onClick={onContactClick}>Book a Demo</button>
          <Link to="/login" className="btn-sticky-primary magnetic">Get Started Free</Link>
        </div>
      </div>
    </div>
  );
}
