import React from 'react';

export default function ContactModal({
  isOpen,
  onClose,
  contactForm,
  setContactForm,
  contactError,
  contactSuccess,
  handleContactSubmit,
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close modal">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        {contactSuccess ? (
          <div className="modal-success-state">
            <div className="success-checkmark-wrapper">
              <svg className="success-checkmark" viewBox="0 0 52 52">
                <circle className="success-checkmark-circle" cx="26" cy="26" r="25" fill="none" />
                <path className="success-checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" />
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
  );
}
