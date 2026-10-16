'use client';
import React from 'react';
import { Database, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function Header({
  activeTab,
  setActiveTab,
}: HeaderProps) {
  const navItems = [
    { id: 'analyze', label: 'Analyse' },
    { id: 'queue', label: 'Approval Queue' },
    { id: 'narratives', label: 'Narratives & Risk' },
    { id: 'governance', label: 'KB Governance' },
  ];

  return (
    <header className="top-bar">
      {/* Left: Brand logo + name */}
      <div className="top-bar-brand">
        <div className="brand-mark">FW</div>
        <span className="brand-title">FinancialWatch</span>
      </div>

      {/* Center: Tabs with underline selection */}
      <nav className="nav-tabs" aria-label="Main Navigation">
        {navItems.map((tab) => (
          <button
            key={tab.id}
            id={`nav-tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
            aria-selected={activeTab === tab.id}
            role="tab"
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Right: Status Indicators */}
      <div className="top-bar-controls">
        {/* Small status dot for database/compliance */}
        <div
          className="status-indicator"
          title="PostgreSQL 16, pgvector and Compliance Gate are active"
        >
          <span className="status-dot pulse-animation" aria-hidden="true" />
          <span>DB & Compliance</span>
        </div>

        {/* Approval-queue persistence indicator */}
        <div
          className="status-indicator"
          title="Approval queue entries persist to PostgreSQL"
        >
          <Database size={12} color="var(--color-primary)" aria-hidden="true" />
          <span>Persistent Queue</span>
        </div>

        {/* Live Engine Ready indicator */}
        <div
          className="status-indicator"
          title="Intelligence Engine is ready for real-time analysis"
        >
          <ShieldCheck size={13} color="var(--color-success)" aria-hidden="true" />
          <span style={{ color: 'var(--color-success)', fontWeight: 500 }}>Live Engine Ready</span>
        </div>
      </div>
    </header>
  );
}
