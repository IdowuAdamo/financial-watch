'use client';
import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Edit3, ShieldAlert, AlertCircle, RefreshCw } from 'lucide-react';
import { FullAnalysisResult } from '../types';

interface ApprovalQueueViewProps {
  apiKey: string;
}

export default function ApprovalQueueView({ apiKey }: ApprovalQueueViewProps) {
  const [items, setItems] = useState<FullAnalysisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingPostId, setEditingPostId] = useState<string | null>(null);
  const [editedFormal, setEditedFormal] = useState('');
  const [editedPidgin, setEditedPidgin] = useState('');

  const getAuthHeaders = (extra: Record<string, string> = {}) => {
    const headers: Record<string, string> = { ...extra };
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    return headers;
  };

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/queue', {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setItems(data);
      }
    } catch (e) {
      console.debug('Error fetching queue:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [apiKey]);

  const handleApprove = async (postId: string) => {
    try {
      const res = await fetch(`/api/queue/${postId}/approve`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        fetchQueue();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleReject = async (postId: string) => {
    const reason = prompt('Please enter audit reason for rejection:');
    if (!reason) return;
    try {
      const res = await fetch(`/api/queue/${postId}/reject`, {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ reason }),
      });
      if (res.ok) {
        fetchQueue();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartEdit = (post: FullAnalysisResult) => {
    setEditingPostId(post.post_id);
    setEditedFormal(post.response_draft.formal_response);
    setEditedPidgin(post.response_draft.pidgin_response || '');
  };

  const handleSaveEdit = async (postId: string) => {
    try {
      const res = await fetch(`/api/queue/${postId}/edit`, {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          edited_formal_response: editedFormal,
          edited_pidgin_response: editedPidgin,
          editor_notes: 'Edited via Command Center HITL Queue',
        }),
      });
      if (res.ok) {
        setEditingPostId(null);
        fetchQueue();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <ShieldAlert size={18} color="var(--color-primary)" />
            <h2 className="card-title">Human-in-the-Loop Counter-Message Approval Queue</h2>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fetchQueue}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh Queue
          </button>
        </div>

        <div className="card-body">
          {/* Governance Notice */}
          <div
            style={{
              backgroundColor: 'var(--color-warning-bg)',
              border: '1px solid var(--color-warning-border)',
              borderRadius: 'var(--radius-md)',
              padding: '10px 14px',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-warning-text)',
              marginBottom: 'var(--space-4)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
            }}
          >
            <AlertCircle size={15} style={{ flexShrink: 0 }} />
            <span>
              <strong>GOVERNANCE RULE:</strong> Auto-posting is strictly prohibited. Every counter-narrative, regulatory clarification, or Pidgin community debunk must be reviewed and authorized by a designated compliance officer before publication.
            </span>
          </div>

          {items.length === 0 ? (
            <div className="empty-state">
              <ShieldAlert size={36} color="var(--text-muted)" style={{ margin: '0 auto 12px' }} />
              <div className="empty-state-title">No pending items in queue</div>
              <p className="empty-state-desc">
                No staged counter-messages currently awaiting review. Process a rumour in the Analyse tab to populate the verification queue.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {items.map((post) => {
                const isEditing = editingPostId === post.post_id;
                const statusBadgeClass =
                  post.approval_status === 'approved'
                    ? 'badge-low'
                    : post.approval_status === 'rejected'
                    ? 'badge-critical'
                    : post.approval_status === 'edited'
                    ? 'badge-simulated'
                    : 'badge-medium';

                return (
                  <div
                    key={post.post_id}
                    style={{
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'var(--bg-surface)',
                      padding: 'var(--space-4)',
                      transition: 'border-color 0.15s ease',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        marginBottom: 'var(--space-2)',
                        gap: 'var(--space-3)',
                      }}
                    >
                      <div>
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-2)',
                            marginBottom: '6px',
                            flexWrap: 'wrap',
                          }}
                        >
                          <span
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: 'var(--font-size-xs)',
                              color: 'var(--text-muted)',
                              fontWeight: 600,
                            }}
                          >
                            {post.post_id}
                          </span>
                          <span
                            className={`badge ${
                              post.classification.category === 'misinformation'
                                ? 'badge-critical'
                                : 'badge-medium'
                            }`}
                          >
                            {post.classification.category}
                          </span>
                          <span className={`badge ${statusBadgeClass}`}>
                            ● {post.approval_status.toUpperCase()}
                          </span>
                        </div>
                        <p
                          style={{
                            fontSize: 'var(--font-size-sm)',
                            color: 'var(--text-primary)',
                            lineHeight: 1.5,
                          }}
                        >
                          &ldquo;{post.raw_text}&rdquo;
                        </p>
                      </div>

                      <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                        {post.approval_status === 'pending' && (
                          <>
                            <button
                              id={`btn-approve-${post.post_id}`}
                              type="button"
                              className="btn btn-success btn-sm"
                              onClick={() => handleApprove(post.post_id)}
                            >
                              <CheckCircle size={13} />
                              Approve
                            </button>
                            <button
                              id={`btn-edit-${post.post_id}`}
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleStartEdit(post)}
                            >
                              <Edit3 size={13} />
                              Edit
                            </button>
                            <button
                              id={`btn-reject-${post.post_id}`}
                              type="button"
                              className="btn btn-danger btn-sm"
                              onClick={() => handleReject(post.post_id)}
                            >
                              <XCircle size={13} />
                              Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Staged Drafts */}
                    {isEditing ? (
                      <div
                        style={{
                          marginTop: 'var(--space-3)',
                          backgroundColor: 'var(--bg-surface-subtle)',
                          padding: 'var(--space-3)',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid var(--border-color)',
                        }}
                      >
                        <div className="form-group" style={{ marginBottom: 'var(--space-2)' }}>
                          <label className="form-label">Edit Formal Response</label>
                          <textarea
                            rows={3}
                            className="form-control"
                            value={editedFormal}
                            onChange={(e) => setEditedFormal(e.target.value)}
                          />
                        </div>
                        <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
                          <label className="form-label">Edit Nigerian Pidgin Debunk</label>
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
                            onClick={() => setEditingPostId(null)}
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            onClick={() => handleSaveEdit(post.post_id)}
                          >
                            Save & Stage
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div
                        style={{
                          marginTop: 'var(--space-2)',
                          backgroundColor: 'var(--bg-surface-subtle)',
                          padding: '10px 12px',
                          borderRadius: 'var(--radius-md)',
                          fontSize: 'var(--font-size-sm)',
                        }}
                      >
                        <div
                          style={{
                            color: 'var(--text-muted)',
                            fontSize: 'var(--font-size-xs)',
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            marginBottom: '4px',
                          }}
                        >
                          Drafted Response:
                        </div>
                        <div style={{ color: 'var(--text-primary)', marginBottom: post.response_draft.pidgin_response ? '6px' : '0' }}>
                          <strong>Formal:</strong> {post.response_draft.formal_response}
                        </div>
                        {post.response_draft.pidgin_response && (
                          <div style={{ color: 'var(--text-primary)' }}>
                            <strong>Pidgin:</strong> {post.response_draft.pidgin_response}
                          </div>
                        )}
                      </div>
                    )}

                    {post.rejection_reason && (
                      <div
                        style={{
                          marginTop: 'var(--space-2)',
                          fontSize: 'var(--font-size-xs)',
                          color: 'var(--color-danger-text)',
                          backgroundColor: 'var(--color-danger-bg)',
                          padding: '6px 10px',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--color-danger-border)',
                        }}
                      >
                        <strong>Rejection Reason:</strong> {post.rejection_reason}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
