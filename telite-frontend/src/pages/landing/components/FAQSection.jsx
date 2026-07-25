import React from 'react';
import FAQItem from './FAQItem';

const FAQS = [
  {
    q: 'Is Telite Systems an LMS?',
    a: 'Telite Systems LMS is a modern learning operations orchestrator and analytics layer. It provides premium role-based administrative consoles, custom organizational boundaries, and advanced AI-driven proactive analytics.',
  },
  {
    q: 'How does the API integration work?',
    a: 'Telite integrates seamlessly via high-speed REST Web Services APIs. It manages user accounts, course categories, metadata, and business operations programmatically. No database customization or plugins are needed.',
  },
  {
    q: 'Is it compliant with modern security standards?',
    a: 'Yes. We designed Telite with enterprise-grade protection. Data is encrypted at rest (AES-256) and in transit (TLS 1.3), supporting strict role hierarchies, row-level access control, and comprehensive logs tracking admin activities.',
  },
  {
    q: 'Can we customize branding for our institution?',
    a: 'Absolutely. Our Enterprise tier supports full white-label capabilities: custom subdomains/domains, custom CSS styling/themes, logo sets, and localized email notifications to match your organization’s identity perfectly.',
  },
  {
    q: 'How long does setting up our workspace take?',
    a: 'Workspaces are provisioned immediately upon sign-up. Setting up organizational categories, bulk importing learners, and synchronizing content via our setup wizards usually takes less than 15 minutes.',
  },
];

function FAQSection() {
  return (
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
  );
}

export default React.memo(FAQSection);
