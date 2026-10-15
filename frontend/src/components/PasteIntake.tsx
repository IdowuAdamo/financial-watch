'use client';
import React, { useState } from 'react';
import { Send, RefreshCw, ChevronDown, Sparkles, RotateCcw } from 'lucide-react';

interface ExamplePost {
  id: string;
  label: string;
  text: string;
  platform: string;
  likes?: number;
  shares?: number;
  timestamp?: string;
  source_adapter: string;
}

export const EXAMPLE_CHIPS: ExamplePost[] = [
  {
    id: 'seed_01',
    label: 'Apex Horizon CAR Rumour',
    text: 'BREAKING: Central Bank of Nigeria has officially revoked the banking license of Apex Horizon Example Bank! Customers are advised to withdraw all their deposits before branches close tomorrow morning.',
    platform: 'X (Twitter)',
    likes: 1240,
    shares: 890,
    timestamp: '2026-10-14T08:30:00Z',
    source_adapter: 'SeedReplayAdapter',
  },
  {
    id: 'seed_03',
    label: 'Heritage Bank Revocation',
    text: 'CBN Press Release Confirmation: The operating banking licence of Heritage Bank Plc was revoked on June 3, 2024, and NDIC was appointed as liquidator.',
    platform: 'X (Twitter)',
    likes: 310,
    shares: 85,
    timestamp: '2026-10-13T14:00:00Z',
    source_adapter: 'SeedReplayAdapter',
  },
  {
    id: 'seed_04',
    label: 'BVN 10-Yr Expiry Warning',
    text: 'URGENT WARNING: Your Bank Verification Number (BVN) will expire after 10 years! If your BVN was registered in 2014, send your details and N5,000 renewal fee to unblock it now.',
    platform: 'Facebook',
    likes: 520,
    shares: 680,
    timestamp: '2026-10-12T11:20:00Z',
    source_adapter: 'SeedReplayAdapter',
  },
  {
    id: 'seed_02',
    label: 'Pidgin Bank Run Broadcast',
    text: 'Make una go withdraw all una money from Apex Horizon Example Bank o! CBN don revoke their license, wahala dey serious! No leave your kudi there!',
    platform: 'WhatsApp Broadcast',
    likes: 45,
    shares: 320,
    timestamp: '2026-10-14T07:15:00Z',
    source_adapter: 'SeedReplayAdapter',
  },
];

interface PasteIntakeProps {
  onAnalyze: (payload: {
    text: string;
    platform?: string;
    likes?: number;
    shares?: number;
    timestamp?: string;
    source_adapter: string;
  }) => void;
  isStreaming: boolean;
  apiKey: string;
  onSelectExample?: (text: string) => void;
}

export default function PasteIntake({ onAnalyze, isStreaming }: PasteIntakeProps) {
  const [text, setText] = useState('');
  const [platform, setPlatform] = useState('X (Twitter)');
  const [likes, setLikes] = useState<string>('');
  const [shares, setShares] = useState<string>('');
  const [timestamp, setTimestamp] = useState<string>('');
  const [activeChipId, setActiveChipId] = useState<string>('');
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);

  const handleApplyExample = (example: ExamplePost) => {
    setActiveChipId(example.id);
    setText(example.text);
    setPlatform(example.platform);
    setLikes(example.likes ? String(example.likes) : '');
    setShares(example.shares ? String(example.shares) : '');
    setTimestamp(example.timestamp || '');
  };

  const handleClear = () => {
    setText('');
    setActiveChipId('');
    setLikes('');
    setShares('');
    setTimestamp('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isStreaming) return;

    const matchedExample = EXAMPLE_CHIPS.find((c) => c.id === activeChipId);
    onAnalyze({
      text: text.trim(),
      platform,
      likes: likes ? parseInt(likes, 10) : undefined,
      shares: shares ? parseInt(shares, 10) : undefined,
      timestamp: timestamp || undefined,
      source_adapter: matchedExample ? 'SeedReplayAdapter' : 'PasteAdapter',
    });
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">
          <Sparkles size={16} color="var(--color-primary)" aria-hidden="true" />
          Analyse Claim
        </h2>
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
          Live Pipeline Intake
        </span>
      </div>

      <div className="card-body">
        {/* Try an example chips */}
        <div style={{ marginBottom: 'var(--space-3)' }}>
          <div
            style={{
              fontSize: 'var(--font-size-xs)',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: '6px',
            }}
          >
            Try an example:
          </div>
          <div className="chips-container" style={{ marginBottom: 0 }}>
            {EXAMPLE_CHIPS.map((chip) => (
              <button
                key={chip.id}
                id={`chip-example-${chip.id}`}
                type="button"
                onClick={() => handleApplyExample(chip)}
                className={`chip ${activeChipId === chip.id ? 'chip-active' : ''}`}
                title={chip.text}
              >
                {chip.label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Main Textarea */}
          <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
            <label htmlFor="input-post-text" className="form-label">
              Claim or Message Text
            </label>
            <textarea
              id="input-post-text"
              rows={5}
              className="form-control"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                if (activeChipId) setActiveChipId('');
              }}
              placeholder="Paste social media post, WhatsApp message, viral rumour, or financial claim (Standard English or Nigerian Pidgin)..."
              maxLength={2000}
              required
            />
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-muted)',
                marginTop: 'var(--space-1)',
              }}
            >
              <span>Max 2,000 characters</span>
              <span
                style={{
                  fontWeight: text.length > 1800 ? 600 : 400,
                  color: text.length > 1950 ? 'var(--color-danger)' : 'var(--text-muted)',
                }}
              >
                {text.length}/2,000
              </span>
            </div>
          </div>

          {/* Collapsible Post Details (Optional) */}
          <div
            style={{
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)',
              overflow: 'hidden',
            }}
          >
            <button
              type="button"
              onClick={() => setIsDetailsOpen(!isDetailsOpen)}
              style={{
                width: '100%',
                padding: '8px 12px',
                background: 'var(--bg-surface-subtle)',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                fontFamily: 'inherit',
              }}
              aria-expanded={isDetailsOpen}
            >
              <span>Post details (optional)</span>
              <ChevronDown
                size={14}
                style={{
                  transform: isDetailsOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s ease',
                }}
              />
            </button>

            {isDetailsOpen && (
              <div
                style={{
                  padding: 'var(--space-3)',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 'var(--space-3)',
                  backgroundColor: 'var(--bg-surface)',
                }}
              >
                <div>
                  <label htmlFor="select-post-platform" className="form-label">
                    Platform
                  </label>
                  <select
                    id="select-post-platform"
                    className="form-control"
                    value={platform}
                    onChange={(e) => setPlatform(e.target.value)}
                    style={{ fontSize: 'var(--font-size-xs)', padding: '6px 8px' }}
                  >
                    <option value="X (Twitter)">X (Twitter)</option>
                    <option value="WhatsApp Broadcast">WhatsApp Broadcast</option>
                    <option value="Facebook">Facebook</option>
                    <option value="Telegram">Telegram</option>
                    <option value="TikTok">TikTok</option>
                    <option value="SMS">SMS Notification</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="input-post-timestamp" className="form-label">
                    Timestamp
                  </label>
                  <input
                    id="input-post-timestamp"
                    type="text"
                    className="form-control"
                    placeholder="e.g. 2026-10-14T08:00:00Z"
                    value={timestamp}
                    onChange={(e) => setTimestamp(e.target.value)}
                    style={{ fontSize: 'var(--font-size-xs)', padding: '6px 8px' }}
                  />
                </div>

                <div>
                  <label htmlFor="input-post-likes" className="form-label">
                    Observed Likes
                  </label>
                  <input
                    id="input-post-likes"
                    type="number"
                    min="0"
                    className="form-control"
                    placeholder="e.g. 850"
                    value={likes}
                    onChange={(e) => setLikes(e.target.value)}
                    style={{ fontSize: 'var(--font-size-xs)', padding: '6px 8px' }}
                  />
                </div>

                <div>
                  <label htmlFor="input-post-shares" className="form-label">
                    Observed Shares
                  </label>
                  <input
                    id="input-post-shares"
                    type="number"
                    min="0"
                    className="form-control"
                    placeholder="e.g. 420"
                    value={shares}
                    onChange={(e) => setShares(e.target.value)}
                    style={{ fontSize: 'var(--font-size-xs)', padding: '6px 8px' }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Form Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleClear}
              disabled={isStreaming || (!text && !likes && !shares && !timestamp)}
            >
              <RotateCcw size={13} />
              Clear
            </button>
            <button
              id="btn-analyze-submit"
              type="submit"
              className="btn btn-primary"
              disabled={isStreaming || !text.trim()}
            >
              {isStreaming ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  <span>Analysing...</span>
                </>
              ) : (
                <>
                  <Send size={14} />
                  <span>Analyse</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
