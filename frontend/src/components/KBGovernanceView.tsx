'use client';
import React, { useState, useEffect } from 'react';
import { Database, ShieldCheck, AlertCircle, RefreshCw, FileText } from 'lucide-react';
import { KBSource } from '../types';

interface KBGovernanceViewProps {
  apiKey: string;
}

export default function KBGovernanceView({ apiKey }: KBGovernanceViewProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/kb/status', {
        headers: apiKey ? { 'X-API-Key': apiKey } : {},
      });
      if (res.ok) {
        setData(await res.json());
      }
    } catch (e) {
      console.debug('Error fetching KB status:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [apiKey]);

  const sources: KBSource[] = data?.sources || [];
  const dbStats = data?.database_stats || {};
  const logs = data?.recent_compliance_logs || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {/* Database Statistics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        <div className="card">
          <div className="card-body" style={{ padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Total Indexed Documents
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-success)' }}>
              {dbStats.total_documents ?? '--'}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              Registered in PostgreSQL
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body" style={{ padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Searchable Vector Chunks
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)' }}>
              {dbStats.total_chunks ?? '--'}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              HNSW Indexed & 1536-dim vectors
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body" style={{ padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Crawler User-Agent
            </div>
            <div
              style={{
                fontSize: 'var(--font-size-sm)',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-primary)',
                fontWeight: 600,
                wordBreak: 'break-all',
              }}
            >
              {data?.crawler_user_agent || 'FinancialWatchBot/1.0'}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Ethical contact URL provided
            </div>
          </div>
        </div>
      </div>

      {/* Sources Registry Table */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <ShieldCheck size={16} color="var(--color-primary)" />
            Authoritative Nigerian Source Governance & Compliance Registry
          </h2>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fetchStatus}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: 'var(--font-size-sm)',
                textAlign: 'left',
              }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    color: 'var(--text-secondary)',
                    fontSize: 'var(--font-size-xs)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}
                >
                  <th style={{ padding: '10px 14px' }}>Source / Agency</th>
                  <th style={{ padding: '10px 14px' }}>Tier</th>
                  <th style={{ padding: '10px 14px' }}>Access Method</th>
                  <th style={{ padding: '10px 14px' }}>Robots.txt Status</th>
                  <th style={{ padding: '10px 14px' }}>Rate Limit / Crawl-Delay</th>
                  <th style={{ padding: '10px 14px' }}>Governance Policy</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((src) => (
                  <tr
                    key={src.id}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      transition: 'background-color 0.15s ease',
                    }}
                  >
                    <td style={{ padding: '12px 14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {src.name}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span className={`badge ${src.tier === 1 ? 'badge-real' : 'badge-medium'}`}>
                        Tier {src.tier}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>
                      {src.access_method}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span
                        className={`badge ${
                          src.robots_status === 'allowed_all' ||
                          src.robots_status === 'allowed_with_disallows' ||
                          src.robots_status === 'allowed_with_crawl_delay'
                            ? 'badge-low'
                            : src.robots_status === '403_bot_protected'
                            ? 'badge-critical'
                            : 'badge-medium'
                        }`}
                      >
                        {src.robots_status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                      {src.crawl_delay_seconds ? `${src.crawl_delay_seconds}s (Honored)` : `${src.rate_limit_seconds || 2.0}s`}
                    </td>
                    <td style={{ padding: '12px 14px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)' }}>
                      {src.terms_of_use_note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Compliance Audit Decision Logs */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <FileText size={16} color="var(--color-primary)" />
            Recent Compliance Gate Audit Decisions (Allow/Deny Records)
          </h3>
        </div>

        <div className="card-body">
          {logs.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
              No recent decision logs recorded.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {logs.slice(-10).map((log: any, idx: number) => (
                <div
                  key={idx}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: 'var(--font-size-xs)',
                    gap: 'var(--space-3)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <span className={`badge ${log.decision === 'ALLOWED' ? 'badge-low' : 'badge-critical'}`}>
                      {log.decision}
                    </span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {log.source_id.toUpperCase()}
                    </span>
                    <span style={{ color: 'var(--text-secondary)' }}>{log.url}</span>
                  </div>
                  <div style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
                    {log.reason}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
