'use client';
import React, { useState } from 'react';
import Header from '../components/Header';
import NoticeBanner from '../components/NoticeBanner';
import PasteIntake from '../components/PasteIntake';
import ResultPanel from '../components/ResultPanel';
import ApprovalQueueView from '../components/ApprovalQueueView';
import NarrativeView from '../components/NarrativeView';
import KBGovernanceView from '../components/KBGovernanceView';
import { PipelineTraceStep, FullAnalysisResult } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

export default function Home() {
  const [activeTab, setActiveTab] = useState<string>('analyze');
  const [traces, setTraces] = useState<PipelineTraceStep[]>([]);
  const [latestResult, setLatestResult] = useState<FullAnalysisResult | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleAnalyze = async (payload: {
    text: string;
    platform?: string;
    likes?: number;
    shares?: number;
    timestamp?: string;
    source_adapter: string;
  }) => {
    setIsStreaming(true);
    setTraces([]);
    setLatestResult(null);
    setErrorMessage(null);

    try {
      // Direct open fetch without requiring any access keys
      const response = await fetch(`${API_BASE_URL}/api/posts/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        if (response.status === 429) {
          throw new Error('Rate limit exceeded (30 requests/minute). Please wait a moment.');
        } else {
          throw new Error(`Server returned HTTP ${response.status}`);
        }
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('text/event-stream')) {
        throw new Error('Analysis endpoint returned unexpected response format. Please verify connection.');
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported on this browser.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // Keep partial event in buffer

        for (const eventStr of events) {
          if (!eventStr.trim()) continue;

          let eventType = 'message';
          let eventData = '';

          const lines = eventStr.split('\n');
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.replace('event: ', '').trim();
            } else if (line.startsWith('data: ')) {
              eventData = line.replace('data: ', '').trim();
            }
          }

          if (eventType === 'agent_trace') {
            try {
              const traceStep: PipelineTraceStep = JSON.parse(eventData);
              setTraces((prev) => {
                const existingIdx = prev.findIndex((t) => t.step_number === traceStep.step_number);
                if (existingIdx >= 0) {
                  const updated = [...prev];
                  updated[existingIdx] = traceStep;
                  return updated;
                } else {
                  return [...prev, traceStep];
                }
              });
            } catch (e) {
              console.debug('Error parsing agent_trace payload:', e);
            }
          } else if (eventType === 'pipeline_complete') {
            try {
              const fullResult: FullAnalysisResult = JSON.parse(eventData);
              setLatestResult(fullResult);
            } catch (e) {
              console.debug('Error parsing pipeline_complete payload:', e);
            }
          } else if (eventType === 'ping') {
            console.debug('SSE heartbeat ping received.');
          }
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred during analysis.');
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="app-container">
      {/* Compact single-line amber disclosure notice */}
      <NoticeBanner />

      {/* Slim top bar */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main className="main-content">
        {activeTab === 'analyze' && (
          <div className="grid-two-cols">
            {/* Left column: Input Card */}
            <div>
              <PasteIntake
                onAnalyze={handleAnalyze}
                isStreaming={isStreaming}
              />
            </div>

            {/* Right column: Result Panel (Verdict, Evidence, Response, Timeline) */}
            <div>
              <ResultPanel
                latestResult={latestResult}
                traces={traces}
                isStreaming={isStreaming}
                errorMessage={errorMessage}
              />
            </div>
          </div>
        )}

        {activeTab === 'queue' && (
          <ApprovalQueueView />
        )}

        {activeTab === 'narratives' && (
          <NarrativeView />
        )}

        {activeTab === 'governance' && (
          <KBGovernanceView />
        )}
      </main>

      <footer
        style={{
          borderTop: '1px solid var(--border-color)',
          backgroundColor: 'var(--bg-surface)',
          padding: 'var(--space-4) var(--space-6)',
          textAlign: 'center',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--text-muted)',
          marginTop: 'auto',
        }}
      >
        FinancialWatch PoC • Grounded Regulatory Intelligence for Nigerian Financial Institutions • PostgreSQL 16 + pgvector
      </footer>
    </div>
  );
}
