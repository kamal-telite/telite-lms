import React, { useState } from 'react';

export default function FAQItem({ item }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className={`faq-item ${isOpen ? 'open' : ''}`}>
      <button className="faq-trigger" onClick={() => setIsOpen(!isOpen)} aria-expanded={isOpen}>
        <span className="faq-question">{item.q}</span>
        <span className="faq-icon-wrap">
          <svg className="faq-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </span>
      </button>
      <div className="faq-content-wrap" style={{ maxHeight: isOpen ? '300px' : '0' }}>
        <div className="faq-content">
          <p>{item.a}</p>
        </div>
      </div>
    </div>
  );
}
