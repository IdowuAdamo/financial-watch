'use client';
import React, { useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Edit3,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Activity,
  Key,
  Calendar,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react';
import { FullAnalysisResult, PipelineTraceStep } from '../types';

interface ResultPanelProps {
  latestResult: FullAnalysisResult | null;
  traces: PipelineTraceStep[];
  isStreaming: boolean;
  errorMessage: string | null;
  onSelectExample?: (text: string) => void;
}

const EXAMPLE_SUGGESTIONS = [
  'Apex Horizon CAR Rumour',
  'Heritage Bank Revocation',
  'BVN 10-Yr Expiry Warning',
  'Pidgin Bank Run Broadcast',
];

export default function ResultPanel({
  latestResult,
  traces,
  isStreaming,
  errorMessage,
  onSelectExample,
}: ResultPanelProps) {
  const [isTimelineOpen, setIsTimelineOpen] = useState(true);
  const [expandedTraceSteps, setExpandedTraceSteps] = useState<Record<number, boolean>>({});
  const [approvalStatus, setApprovalStatus] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedFormal, setEditedFormal] = useState('');
  const [editedPidgin, setEditedPidgin] = useState('');

  // Keep local approval status synchronized if latestResult changes
  const currentStatus = approvalStatus || latestResult?.approval_status || 'pending';

  const toggleTraceStep = (stepNum: number) => {
    setExpandedTraceSteps((prev) => ({ ...prev, [stepNum]: !prev[stepNum] }));
  };

  const handleApprove = async () => {
    if (!latestResult) return;
    try {
      const res = await fetch(`/api/queue/${latestResult.post_id}/approve`, {
        method: 'POST',
      });
      if (res.ok) {
        setApprovalStatus('approved');
      }
    } catch (e) {
      console.error('Approve failed:', e);
    }
  };

  const handleStartEdit = () => {
    if (!latestResult) return;
    setEditedFormal(latestResult.response_draft.formal_response);
    setEditedPidgin(latestResult.response_draft.pidgin_response || '');
    setIsEditing(true);
  };

  const handleSaveEdit = async () => {
    if (!latestResult) return;
    try {
      const res = await fetch(`/api/queue/${latestResult.post_id}/edit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          edited_formal_response: editedFormal,
          edited_pidgin_response: editedPidgin,
          editor_notes: 'Edited via Command Center Result Panel',
        }),
      });
      if (res.ok) {
        setApprovalStatus('edited');
        if (latestResult.response_draft) {
          latestResult.response_draft.formal_response = editedFormal;
          latestResult.response_draft.pidgin_response = editedPidgin;
        }
        setIsEditing(false);
      }
    } catch (e) {
      console.error('Save edit failed:', e);
    }
  };

  const handleReject = async () => {
    if (!latestResult) return;
    const reason = prompt('Please enter audit reason for rejection:');
    if (!reason) return;
    try {
      const res = await fetch(`/api/queue/${latestResult.post_id}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason }),
      });
      if (res.ok) {
        setApprovalStatus('rejected');
      }
    } catch (e) {
      console.error('Reject failed:', e);
    }
  };

  // 1. Error State
  if (errorMessage) {
    return (
      <div className="card">
        <div className="card-header" style={{ borderBottomColor: 'var(--color-danger-border)' }}>
          <h2 className="card-title" style={{ color: 'var(--color-danger)' }}>
            <AlertTriangle size={16} />
            Analysis Pipeline Notice
          </h2>
        </div>
        <div className="card-body">
          <div
            style={{
              padding: 'var(--space-4)',
              backgroundColor: 'var(--color-danger-bg)',
              border: '1px solid var(--color-danger-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-danger-text)',
              marginBottom: 'var(--space-4)',
              fontSize: 'var(--font-size-base)',
            }}
          >
            <strong>Notice:</strong> {errorMessage}
          </div>
        </div>
      </div>
    );
  }

  // 2. Loading State (Streaming but no final result yet)
  if (isStreaming && !latestResult) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <Activity size={16} color="var(--color-primary)" className="pulse-animation" />
            Verification Pipeline Active
          </h2>
          <span className="badge badge-simulated">Streaming Stages</span>
        </div>
        <div className="card-body">
          <div
            style={{
              padding: 'var(--space-4)',
              backgroundColor: 'var(--color-primary-subtle)',
              border: '1px solid var(--color-primary-border)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
            }}
          >
            <div className="status-dot pulse-animation" style={{ backgroundColor: 'var(--color-primary)' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)', color: 'var(--color-primary)' }}>
                Executing Intelligence Pipeline Stages
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                Authoritative retrieval and verification in progress...
              </div>
            </div>
          </div>

          {/* Streaming Live Timeline */}
          {traces.length > 0 && (
            <div className="timeline">
              <div
                style={{
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                How this is being decided ({traces.length} stages active):
              </div>
              {traces.map((trace) => (
                <div key={`${trace.step_number}-${trace.timestamp}`} className="timeline-step">
                  <div className="timeline-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <span className={`timeline-step-num ${trace.status === 'completed' ? 'done' : ''}`}>
                        {trace.step_number}
                      </span>
                      <div>
                        <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
                          {trace.agent_name.replace(/agent/gi, 'Stage').replace(/multi-agent/gi, 'Pipeline')}
                        </div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                          {trace.output_summary}
                        </div>
                      </div>
                    </div>
                    <span
                      className={`badge ${
                        trace.status === 'completed'
                          ? 'badge-low'
                          : trace.status === 'running'
                          ? 'badge-simulated'
                          : 'badge-medium'
                      }`}
                    >
                      {trace.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // 3. Empty State (No analysis run yet)
  if (!latestResult) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <ShieldCheck size={16} color="var(--color-primary)" aria-hidden="true" />
            Intelligence & Verification Results
          </h2>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Awaiting input
          </span>
        </div>
        <div className="card-body">
          <div className="empty-state">
            <div className="empty-state-icon">
              <Layers size={40} strokeWidth={1.5} color="var(--color-primary)" />
            </div>
            <h3 className="empty-state-title">Automated Regulatory Intelligence</h3>
            <p className="empty-state-desc">
              Paste a social post, rumour, or financial claim on the left to verify its factual accuracy against authoritative CBN and NDIC archives, score institutional risk, and generate compliance-validated response drafts.
            </p>

            {/* Engine Status Indicator in Empty State */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                backgroundColor: 'var(--color-success-bg)',
                border: '1px solid var(--color-success-border)',
                color: 'var(--color-success-text)',
                padding: '5px 12px',
                borderRadius: 'var(--radius-full)',
                fontSize: 'var(--font-size-xs)',
                marginBottom: 'var(--space-4)',
              }}
            >
              <CheckCircle size={14} />
              <span>Multi-Agent Engine Active • Live Intelligence Ready</span>
            </div>

            {/* Quick Example Suggestions */}
            <div>
              <div
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--text-muted)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                Quick example scenarios to evaluate:
              </div>
              <div className="chips-container" style={{ justifyContent: 'center' }}>
                {EXAMPLE_SUGGESTIONS.map((label, idx) => (
                  <span
                    key={idx}
                    className="chip"
                    style={{ cursor: 'default' }}
                  >
                    <Sparkles size={11} color="var(--color-primary)" />
                    {label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 4. Completed Result State
  const verdict = latestResult.verification.verdict.toLowerCase();
  const isContradicted = verdict === 'contradicted';
  const isSupported = verdict === 'supported';
  const confidencePercent = Math.round(latestResult.verification.confidence * 100);

  const verdictBadgeClass = isContradicted
    ? 'badge-critical'
    : isSupported
    ? 'badge-low'
    : 'badge-medium';

  const verdictLabel = isContradicted
    ? 'Contradicted'
    : isSupported
    ? 'Supported'
    : 'Insufficient Evidence';

  const riskLevel = latestResult.risk.risk_level.toUpperCase();
  const riskBadgeClass =
    riskLevel === 'CRITICAL'
      ? 'badge-critical'
      : riskLevel === 'HIGH'
      ? 'badge-high'
      : riskLevel === 'MEDIUM'
      ? 'badge-medium'
      : 'badge-low';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {/* 4A: Verdict & Risk Score Card */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <h2 className="card-title">
              <ShieldCheck size={16} color="var(--color-primary)" aria-hidden="true" />
              Verdict & Risk Assessment
            </h2>
          </div>
          <span className={`badge ${verdictBadgeClass}`} style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
            {verdictLabel}
          </span>
        </div>

        <div className="card-body">
          {/* Top Verdict Stats Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 'var(--space-4)',
              paddingBottom: 'var(--space-4)',
              borderBottom: '1px solid var(--border-color)',
              marginBottom: 'var(--space-4)',
            }}
          >
            {/* Confidence Gauge */}
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 'var(--space-1)',
                }}
              >
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                  Confidence Score
                </span>
                <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700 }}>
                  {confidencePercent}%
                </span>
              </div>
              <div className="progress-container">
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${confidencePercent}%`,
                    backgroundColor: isContradicted
                      ? 'var(--color-danger)'
                      : isSupported
                      ? 'var(--color-success)'
                      : 'var(--color-warning)',
                  }}
                />
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: '4px' }}>
                {latestResult.verification.cited_passages.length} authoritative passage(s) cited
              </div>
            </div>

            {/* Risk Score Indicator */}
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 'var(--space-1)',
                }}
              >
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                  Risk Score
                </span>
                <span className={`badge ${riskBadgeClass}`}>
                  {riskLevel} • {latestResult.risk.total_score}/100
                </span>
              </div>
              <div className="progress-container">
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${Math.min(latestResult.risk.total_score, 100)}%`,
                    backgroundColor:
                      riskLevel === 'CRITICAL'
                        ? 'var(--color-danger)'
                        : riskLevel === 'HIGH'
                        ? '#ea580c'
                        : riskLevel === 'MEDIUM'
                        ? 'var(--color-warning)'
                        : 'var(--color-success)',
                  }}
                />
              </div>
              <div
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--text-secondary)',
                  marginTop: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <span>Components:</span>
                <strong style={{ color: 'var(--text-primary)' }}>
                  {latestResult.risk.active_components.join(' + ')}
                </strong>
              </div>
            </div>
          </div>

          {/* Reasoning */}
          <div style={{ marginBottom: 'var(--space-3)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Reasoning & Synthesis:
            </div>
            <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {latestResult.verification.reasoning}
            </p>
          </div>

          {/* Renormalisation Note if any */}
          {latestResult.risk.renormalised_note && (
            <div
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-warning-text)',
                backgroundColor: 'var(--color-warning-bg)',
                padding: '6px 10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-warning-border)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Info size={13} style={{ flexShrink: 0 }} />
              <span>{latestResult.risk.renormalised_note}</span>
            </div>
          )}
        </div>
      </div>

      {/* 4B: Ground-Truth Evidence List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Layers size={16} color="var(--color-primary)" aria-hidden="true" />
            Authoritative Evidence Citations ({latestResult.verification.cited_passages.length})
          </h3>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Authoritative Registry Match
          </span>
        </div>

        <div className="card-body">
          {latestResult.verification.cited_passages.length === 0 ? (
            <div
              style={{
                padding: 'var(--space-4)',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-sm)',
                fontStyle: 'italic',
                backgroundColor: 'var(--bg-surface-subtle)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              No matching passages cited from authoritative regulatory records.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {latestResult.verification.cited_passages.map((cite) => {
                const isHeuristic = cite.chunk_id?.startsWith('scam_advisory_');
                const borderClass = isHeuristic
                  ? 'evidence-item-heuristic'
                  : cite.is_simulated
                  ? 'evidence-item-simulated'
                  : 'evidence-item-real';

                return (
                  <div key={cite.chunk_id} className={`evidence-item ${borderClass}`}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: 'var(--space-1)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <span style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
                          {cite.source}
                        </span>
                        <span className="badge badge-low" style={{ fontSize: '0.7rem' }}>
                          Tier {cite.tier}
                        </span>
                        {cite.publish_date && (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '3px',
                              fontSize: 'var(--font-size-xs)',
                              color: 'var(--text-muted)',
                            }}
                          >
                            <Calendar size={11} />
                            {cite.publish_date}
                          </span>
                        )}
                      </div>

                      {/* Badge REAL / SIMULATED / TITLE-ONLY / INTERNAL HEURISTIC */}
                      <div style={{ display: 'flex', gap: '4px' }}>
                        {isHeuristic ? (
                          <span className="badge badge-heuristic">INTERNAL HEURISTIC</span>
                        ) : (
                          <>
                            {cite.is_simulated && <span className="badge badge-simulated">SIMULATED</span>}
                            {cite.is_title_only && <span className="badge badge-title-only">TITLE-ONLY</span>}
                            {!cite.is_simulated && !cite.is_title_only && (
                              <span className="badge badge-real">REAL</span>
                            )}
                          </>
                        )}
                      </div>
                    </div>

                    {/* Quoted Span Snippet */}
                    <div
                      style={{
                        fontSize: 'var(--font-size-sm)',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.5,
                        marginBottom: 'var(--space-2)',
                      }}
                    >
                      &ldquo;{cite.snippet}&rdquo;
                    </div>

                    {/* Source Link */}
                    {isHeuristic ? (
                      <div
                        style={{
                          fontSize: 'var(--font-size-xs)',
                          color: 'var(--color-heuristic-text)',
                          fontStyle: 'italic',
                        }}
                      >
                        Internal security heuristic rule; not official circular text.
                      </div>
                    ) : (
                      cite.url &&
                      !cite.url.startsWith('internal://') && (
                        <div>
                          <a
                            href={cite.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              fontSize: 'var(--font-size-xs)',
                              color: 'var(--color-primary)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              textDecoration: 'none',
                              fontWeight: 500,
                            }}
                          >
                            <span>Official Source Link</span>
                            <ExternalLink size={11} />
                          </a>
                        </div>
                      )
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 4C: Drafted Response & Human Approval Card */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <h3 className="card-title">
              <Edit3 size={16} color="var(--color-primary)" aria-hidden="true" />
              Drafted Response & Verification Actions
            </h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <span
              className={`badge ${
                latestResult.response_draft.citation_validation_passed
                  ? 'badge-low'
                  : 'badge-critical'
              }`}
            >
              Citations:{' '}
              {latestResult.response_draft.citation_validation_passed ? 'VALIDATED' : 'FLAGGED'}
            </span>
            <span
              className={`badge ${
                currentStatus === 'approved'
                  ? 'badge-low'
                  : currentStatus === 'rejected'
                  ? 'badge-critical'
                  : currentStatus === 'edited'
                  ? 'badge-simulated'
                  : 'badge-medium'
              }`}
            >
              ● {currentStatus.toUpperCase()}
            </span>
          </div>
        </div>

        <div className="card-body">
          {isEditing ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <div>
                <label className="form-label">Edit Formal Corporate Statement</label>
                <textarea
                  rows={3}
                  className="form-control"
                  value={editedFormal}
                  onChange={(e) => setEditedFormal(e.target.value)}
                />
              </div>
              <div>
                <label className="form-label">Edit Nigerian Pidgin Community Clarification</label>
                <textarea
                  rows={2}
                  className="form-control"
                  value={editedPidgin}
                  onChange={(e) => setEditedPidgin(e.target.value)}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setIsEditing(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleSaveEdit}
                >
                  Save & Stage
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {/* Formal Response */}
              <div
                style={{
                  backgroundColor: 'var(--bg-surface-subtle)',
                  padding: 'var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                }}
              >
                <div
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    marginBottom: '4px',
                  }}
                >
                  Formal Statement:
                </div>
                <div style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  {latestResult.response_draft.formal_response}
                </div>
              </div>

              {/* Pidgin Response if present */}
              {latestResult.response_draft.pidgin_response && (
                <div
                  style={{
                    backgroundColor: 'var(--bg-surface-subtle)',
                    padding: 'var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div
                    style={{
                      fontSize: 'var(--font-size-xs)',
                      fontWeight: 600,
                      color: 'var(--text-muted)',
                      textTransform: 'uppercase',
                      marginBottom: '4px',
                    }}
                  >
                    Nigerian Pidgin Community Debunk:
                  </div>
                  <div style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                    {latestResult.response_draft.pidgin_response}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Action Buttons: Approve / Edit / Reject */}
        <div className="card-footer" style={{ justifyContent: 'space-between' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            HITL Review Required prior to publication
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <button
              id={`btn-approve-${latestResult.post_id}`}
              type="button"
              className="btn btn-success btn-sm"
              onClick={handleApprove}
              disabled={currentStatus === 'approved'}
            >
              <CheckCircle size={14} />
              Approve
            </button>
            <button
              id={`btn-edit-${latestResult.post_id}`}
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleStartEdit}
            >
              <Edit3 size={14} />
              Edit
            </button>
            <button
              id={`btn-reject-${latestResult.post_id}`}
              type="button"
              className="btn btn-danger btn-sm"
              onClick={handleReject}
              disabled={currentStatus === 'rejected'}
            >
              <XCircle size={14} />
              Reject
            </button>
          </div>
        </div>
      </div>

      {/* 4D: Collapsible "How this was decided" Timeline */}
      <div className="card">
        <div
          className="card-header"
          onClick={() => setIsTimelineOpen(!isTimelineOpen)}
          style={{ cursor: 'pointer', userSelect: 'none' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Activity size={16} color="var(--color-primary)" />
            <h3 className="card-title">
              How this was decided ({traces.length || latestResult.traces?.length || 0} stages)
            </h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
              Execution Trace
            </span>
            {isTimelineOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </div>

        {isTimelineOpen && (
          <div className="card-body">
            <div className="timeline">
              {(traces.length > 0 ? traces : latestResult.traces || []).map((trace) => {
                const isExpanded = !!expandedTraceSteps[trace.step_number];
                const isDone = trace.status === 'completed';

                return (
                  <div key={`${trace.step_number}-${trace.timestamp}`} className="timeline-step">
                    <div
                      className="timeline-header"
                      onClick={() => toggleTraceStep(trace.step_number)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                        <span className={`timeline-step-num ${isDone ? 'done' : ''}`}>
                          {trace.step_number}
                        </span>
                        <div>
                          <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
                            {trace.agent_name.replace(/agent/gi, 'Stage').replace(/multi-agent/gi, 'Pipeline')}
                          </div>
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                            {trace.output_summary}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <span
                          className={`badge ${
                            isDone ? 'badge-low' : trace.status === 'bypassed' ? 'badge-medium' : 'badge-high'
                          }`}
                        >
                          {trace.status}
                        </span>
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </div>
                    </div>

                    {isExpanded && trace.details && (
                      <div className="timeline-details">
                        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>
                          {JSON.stringify(trace.details, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
