'use client';
import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function NoticeBanner() {
  return (
    <aside
      id="fictional-notice-banner"
      className="notice-banner"
      role="note"
      aria-label="Simulation Disclosure"
    >
      <div className="notice-banner-text">
        <AlertCircle size={14} style={{ flexShrink: 0 }} aria-hidden="true" />
        <span>
          <strong>Notice:</strong> Bank-specific rumours and client institutions (Apex Horizon Example Bank, Meridian Mock Bank, Northbridge Example Bank, Kreston Test Bank) are fictional for demonstration. Authoritative regulatory references are real.
        </span>
      </div>
      <div style={{ flexShrink: 0, opacity: 0.85, fontSize: '0.75rem', fontWeight: 500 }}>
        NDPR Safeguards Active
      </div>
    </aside>
  );
}
