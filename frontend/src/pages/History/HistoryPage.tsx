import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { ApiService } from '../../services/api';
import type { AnalysisStatusResponse } from '../../services/api';

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [history, setHistory] = useState<AnalysisStatusResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const loadHistory = () => {
    setLoading(true);
    ApiService.getAnalysisHistory()
      .then(setHistory)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleClearHistory = async () => {
    if (window.confirm('Are you sure you want to clear your assessment history?')) {
      try {
        await ApiService.clearAnalysisHistory();
        loadHistory();
      } catch { }
    }
  };

  return (
    <PageContainer className="max-w-4xl py-8">
      <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: 20, marginBottom: 32, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', margin: 0 }}>Assessment Run History</h1>
          <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
            Trace and review previous multi-agent execution pipeline runs.
          </p>
        </div>
        {history.length > 0 && (
          <button
            onClick={handleClearHistory}
            style={{
              borderRadius: 8,
              background: '#fff',
              border: '1px solid #fecaca',
              color: '#dc2626',
              padding: '8px 16px',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 1px 2px rgba(220,38,38,0.05)',
              transition: 'all 0.15s'
            }}
          >
            Clear History
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px 0', color: '#64748b' }}>
          <div style={{ display: 'inline-block', width: 32, height: 32, border: '3px solid #e2e8f0', borderTop: '3px solid #2563eb', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
          <p style={{ marginTop: 12, fontSize: 13, fontWeight: 500 }}>Loading history...</p>
        </div>
      ) : history.length === 0 ? (
        <div style={{ borderRadius: 14, border: '1px solid #e2e8f0', background: '#fff', padding: '48px 32px', textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>📂</div>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', margin: '0 0 6px' }}>No previous assessment runs</h3>
          <p style={{ fontSize: 13, color: '#64748b', margin: '0 0 20px', maxWidth: 320, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.5 }}>
            No assessment pipelines have been executed yet. Satisfy all document slots in the workspace and click Start Assessment to create runs.
          </p>
          <button
            onClick={() => navigate('/intake')}
            style={{
              borderRadius: 8,
              background: '#2563eb',
              color: '#fff',
              border: 'none',
              padding: '8px 18px',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(37,99,235,0.2)'
            }}
          >
            Go to Workspace
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {history.map((job) => {
            const dateStr = new Date(job.created_at).toLocaleString();
            const shortId = `CLAIM-${job.job_id.slice(0, 8).toUpperCase()}`;

            // Setup status badges
            let badgeBg = '#f1f5f9';
            let badgeColor = '#475569';
            let statusLabel = job.status.toUpperCase();

            if (job.status === 'completed') {
              badgeBg = '#d1fae5';
              badgeColor = '#065f46';
              statusLabel = 'Completed';
            } else if (job.status === 'failed') {
              badgeBg = '#fee2e2';
              badgeColor = '#991b1b';
              statusLabel = 'Failed';
            } else if (job.status === 'awaiting_approval') {
              badgeBg = '#fef3c7';
              badgeColor = '#92400e';
              statusLabel = 'Awaiting Approval';
            } else if (job.status === 'processing') {
              badgeBg = '#dbeafe';
              badgeColor = '#1e40af';
              statusLabel = 'Processing';
            }

            return (
              <div
                key={job.job_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '16px 20px',
                  borderRadius: 12,
                  border: '1px solid #e2e8f0',
                  background: '#fff',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#1e293b', fontFamily: 'monospace' }}>
                      {shortId}
                    </span>
                    <span style={{
                      fontSize: 10,
                      fontWeight: 700,
                      background: badgeBg,
                      color: badgeColor,
                      padding: '2px 8px',
                      borderRadius: 12,
                      textTransform: 'uppercase',
                      letterSpacing: '0.03em'
                    }}>
                      {statusLabel}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#64748b' }}>
                    <span>{dateStr}</span>
                    <span>&bull;</span>
                    <span style={{ maxWidth: 450, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={job.message}>
                      {job.message}
                    </span>
                  </div>
                </div>

                <div>
                  {job.status === 'completed' ? (
                    <button
                      onClick={() => navigate(`/results?job_id=${job.job_id}`)}
                      style={{
                        borderRadius: 8,
                        background: '#fff',
                        border: '1px solid #cbd5e1',
                        color: '#1e293b',
                        padding: '8px 16px',
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: 'pointer',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                        transition: 'all 0.15s'
                      }}
                    >
                      View Report
                    </button>
                  ) : (
                    <button
                      onClick={() => navigate(`/intake?job_id=${job.job_id}`)}
                      style={{
                        borderRadius: 8,
                        background: '#2563eb',
                        border: 'none',
                        color: '#fff',
                        padding: '8px 16px',
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: 'pointer',
                        boxShadow: '0 1px 2px rgba(37,99,235,0.15)',
                        transition: 'all 0.15s'
                      }}
                    >
                      {job.status === 'failed' ? 'View Details' : 'Resume Run'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </PageContainer>
  );
};
