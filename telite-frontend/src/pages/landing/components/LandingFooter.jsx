import React from 'react';

export default function LandingFooter({ dashboardLink, newsletterEmail, newsletterSuccess, setNewsletterEmail, handleNewsletterSubmit }) {
  return (
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
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
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
  );
}
