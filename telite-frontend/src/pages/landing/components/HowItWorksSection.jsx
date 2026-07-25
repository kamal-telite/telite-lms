import React from 'react';

const STEPS = [
  ["1", "Create your workspace", "Set up your organisation, configure allowed domains, and invite your first admins. Under five minutes."],
  ["2", "Add users and courses", "Bulk import learners, create learning categories, publish courses with modules, and assign tasks."],
  ["3", "Track and optimise", "Monitor real-time progress, PAL scores, and completion rates. Export reports and act on at-risk alerts."],
];

export default function HowItWorksSection() {
  return (
    <section id="howitworks">
      <div className="inner">
        <div className="steps-header">
          <span className="section-eyebrow">How it works</span>
          <h2 className="section-title">Up and running in three steps</h2>
          <p className="section-sub">No complex setup. Your team can be learning within hours.</p>
        </div>
        <div className="steps-row">
          <div className="step-connector" />
          {STEPS.map(([num, title, desc]) => (
            <div className="step-card" key={num}>
              <div className="step-num">{num}</div>
              <div className="step-card-body">
                <h3 className="step-title">{title}</h3>
                <p className="step-desc">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
