import React from 'react';
import './ProductFrame.css';

/**
 * ProductFrame provides the "Browser" aesthetic for our dashboard previews.
 */
export default function ProductFrame({ children, title = "Telite LMS Dashboard" }) {
  return (
    <div className="product-frame">
      <div className="frame-header">
        <div className="frame-dots">
          <span className="dot red"></span>
          <span className="dot yellow"></span>
          <span className="dot green"></span>
        </div>
        <div className="frame-title">{title}</div>
      </div>
      <div className="frame-content">
        {children}
      </div>
    </div>
  );
}
