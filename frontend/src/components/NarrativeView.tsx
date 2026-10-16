'use client';
import React, { useState, useEffect } from 'react';
import { TrendingUp, BarChart2, AlertTriangle, ShieldCheck, Activity } from 'lucide-react';

export default function NarrativeView() {
  const [narratives, setNarratives] = useState<any[]>([]);
  const [riskOverview, setRiskOverview] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [narrRes, riskRes] = await Promise.all([
          fetch('/api/narratives'),
          fetch('/api/risk'),
        ]);
        if (narrRes.ok) setNarratives(await narrRes.json());
        if (riskRes.ok) setRiskOverview(await riskRes.json());
      } catch (e) {
        console.debug('Error fetching narratives:', e);
      }
    };
    fetchData();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {/* Top metrics summary cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        <div className="card">
          <div className="card-body" style={{ padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Average Stream Risk
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-warning)' }}>
              {riskOverview ? `${riskOverview.average_risk_score}/100` : '--'}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              Normalized Heuristic Metric
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body" style={{ padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Critical Threats
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-danger)' }}>
              {riskOverview ? riskOverview.distribution.CRITICAL : 0}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              Active bank-run / revocation claims
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body" style={{ padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
              High Risk (Scams)
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ea580c' }}>
              {riskOverview ? riskOverview.distribution.HIGH : 0}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              Credential & fee phishing
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body" style={{ padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Analyzed Stream Volume
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)' }}>
              {riskOverview ? riskOverview.total_analyzed_posts : 0}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              Session items logged
            </div>
          </div>
        </div>
      </div>

      {/* Narrative Clusters Table / Cards */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <TrendingUp size={16} color="var(--color-primary)" />
            Thematic Narrative Clusters & Spread Velocity
          </h2>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            {narratives.length} Active Clusters
          </span>
        </div>

        <div className="card-body">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {narratives.map((cluster) => {
              const sevBadgeClass =
                cluster.base_severity >= 80
                  ? 'badge-critical'
                  : cluster.base_severity >= 50
                  ? 'badge-high'
                  : 'badge-low';

              return (
                <div
                  key={cluster.cluster_id}
                  style={{
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-3) var(--space-4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 'var(--space-4)',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: '4px' }}>
                      <span style={{ fontSize: 'var(--font-size-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {cluster.title}
                      </span>
                      <span className={`badge ${sevBadgeClass}`}>
                        Severity {cluster.base_severity}
                      </span>
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                      Archetype ID: {cluster.cluster_id}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-6)' }}>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>Observed Posts</div>
                      <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700 }}>{cluster.post_count}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>Velocity Rating</div>
                      <div
                        style={{
                          fontSize: 'var(--font-size-sm)',
                          fontWeight: 600,
                          color: cluster.estimated_velocity === 'High' ? 'var(--color-danger)' : 'var(--text-secondary)',
                        }}
                      >
                        {cluster.estimated_velocity}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Mathematical Risk Methodology Note */}
      <div className="card">
        <div className="card-body" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
            <BarChart2 size={15} color="var(--color-primary)" />
            Heuristic Risk Methodology & Dynamic Renormalisation
          </div>
          <p style={{ marginBottom: '6px' }}>
            <strong>Formula:</strong> Clamped 0–100 score computed from Severity (0.40), Verification Verdict (0.30), Reach (0.15), and Velocity (0.15).
          </p>
          <p style={{ color: 'var(--color-warning-text)' }}>
            <strong>Dynamic Renormalisation:</strong> If engagement counts or timestamps are omitted in the paste form, missing factors are dropped and the remaining weights (Severity and Verdict) are renormalised to sum to 1.0, ensuring mathematical integrity.
          </p>
        </div>
      </div>
    </div>
  );
}
