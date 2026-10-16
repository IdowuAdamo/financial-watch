'use client';
import React, { useState, useEffect } from 'react';
import { Key, Database, ShieldCheck, Check, X } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  apiKey: string;
  setApiKey: (key: string) => void;
  showKeyModal?: boolean;
  setShowKeyModal?: (show: boolean) => void;
}

export default function Header({
  activeTab,
  setActiveTab,
  apiKey,
  setApiKey,
  showKeyModal: controlledShowKeyModal,
  setShowKeyModal: controlledSetShowKeyModal,
}: HeaderProps) {
  const [internalShowKeyModal, setInternalShowKeyModal] = useState(false);
  const showKeyModal = controlledShowKeyModal !== undefined ? controlledShowKeyModal : internalShowKeyModal;
  const setShowKeyModal = controlledSetShowKeyModal || setInternalShowKeyModal;

  const [tempKey, setTempKey] = useState(apiKey);

  useEffect(() => {
    setTempKey(apiKey);
  }, [apiKey]);

  const handleSaveKey = () => {
    setApiKey(tempKey.trim());
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('FW_ACCESS_KEY', tempKey.trim());
    }
    setShowKeyModal(false);
  };

  const navItems = [
    { id: 'analyze', label: 'Analyse' },
    { id: 'queue', label: 'Approval Queue' },
    { id: 'narratives', label: 'Narratives & Risk' },
    { id: 'governance', label: 'KB Governance' },
  ];

  return (
    <>
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

        {/* Right: Status Indicators + API Key button */}
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

          {/* Key icon button for the API key */}
          <button
            id="btn-access-key-toggle"
            type="button"
            onClick={() => setShowKeyModal(true)}
            className={`btn btn-sm ${apiKey ? 'btn-secondary' : 'btn-outline'}`}
            title="Configure Runtime Access Key"
            aria-label="Configure Runtime Access Key"
          >
            <Key size={14} aria-hidden="true" />
            <span>{apiKey ? 'API Key' : 'Enter Key'}</span>
            {apiKey && (
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-success)',
                }}
              />
            )}
          </button>
        </div>
      </header>

      {/* Access Key Modal */}
      {showKeyModal && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowKeyModal(false);
          }}
        >
          <div className="modal-content">
            <div className="card-header">
              <h3 id="modal-title" className="card-title">
                <Key size={16} color="var(--color-primary)" aria-hidden="true" />
                Runtime Access Key
              </h3>
              <button
                type="button"
                className="btn btn-secondary btn-icon"
                onClick={() => setShowKeyModal(false)}
                aria-label="Close dialog"
              >
                <X size={16} />
              </button>
            </div>

            <div className="card-body">
              <p
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--text-secondary)',
                  marginBottom: 'var(--space-4)',
                  lineHeight: 1.5,
                }}
              >
                Deployed requests through CloudFront are authenticated automatically. If you wish to use a custom evaluation access key or test external client credentials, enter it below. It will be passed via the{' '}
                <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--bg-surface-subtle)', padding: '2px 4px', borderRadius: '4px' }}>
                  X-API-Key
                </code>{' '}
                header.
              </p>

              <div className="form-group">
                <label htmlFor="input-runtime-api-key" className="form-label">
                  API Key Value
                </label>
                <input
                  id="input-runtime-api-key"
                  type="text"
                  className="form-control"
                  value={tempKey}
                  onChange={(e) => setTempKey(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleSaveKey();
                    }
                  }}
                  placeholder="Enter custom API access key (optional)"
                  autoFocus
                />
              </div>

              {apiKey && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-success)',
                    fontWeight: 500,
                  }}
                >
                  <Check size={14} />
                  <span>Access key active in this browser session</span>
                </div>
              )}
            </div>

            <div className="card-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowKeyModal(false)}
              >
                Cancel
              </button>
              <button
                id="btn-save-runtime-key"
                type="button"
                className="btn btn-primary"
                onClick={handleSaveKey}
              >
                Save Key
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
