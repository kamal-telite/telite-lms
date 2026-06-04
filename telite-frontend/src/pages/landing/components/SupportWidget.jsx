import React, { useRef } from 'react';
import { useFocusTrap } from '../../../hooks/useFocusTrap';

export default function SupportWidget({ isOpen, onClose }) {
  const panelRef = useRef(null);
  useFocusTrap(isOpen, panelRef);

  if (!isOpen) return null;

  return (
    <div className="support-widget-panel" ref={panelRef} role="dialog" aria-modal="true" aria-label="Support Options">
      <div className="widget-panel-header">
        <div>
          <h4>Telite Support Hub</h4>
          <p>How can we help you today?</p>
        </div>
        <button className="widget-close-btn" onClick={onClose} aria-label="Close support menu">×</button>
      </div>
      <div className="widget-panel-body">
        <a href="#faq" className="widget-link-item" onClick={onClose}>
          <div className="widget-item-icon">
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="widget-item-content">
            <h5>Read FAQs</h5>
            <p>Find quick answers to common questions</p>
          </div>
        </a>
        <a href="mailto:support@telitesystems.com" className="widget-link-item">
          <div className="widget-item-icon">
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div className="widget-item-content">
            <h5>Email Support</h5>
            <p>Get in touch with our helpdesk team</p>
          </div>
        </a>
      </div>
    </div>
  );
}
