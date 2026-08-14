import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { ApiService } from '../../services/api';

// Cost Flow Visualizer Component (SVG Adjudication Chain)
const CostFlowVisualizer: React.FC<{
  billed: number;
  primaryPaid: number;
  secondaryPaid: number;
  patientOwes: number;
  primaryInsurer: string;
  secondaryInsurer: string;
  currencySymbol: string;
  providerName?: string;
}> = ({ billed, primaryPaid, secondaryPaid, patientOwes, primaryInsurer, secondaryInsurer, currencySymbol, providerName }) => {
  const hasSecondary = !!secondaryInsurer && secondaryInsurer.trim() !== "";
  const displayProvider = providerName || "Healthcare Provider";

  return (
    <div className="flex flex-col items-center py-8 bg-slate-50/50 rounded-2xl border border-slate-200/80 shadow-inner">
      {/* Node: Provider */}
      <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-xl border border-slate-200 shadow-sm w-64 hover:translate-y-[-2px] transition-transform duration-200">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 text-lg shadow-sm">
          🏥
        </div>
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Medical Provider</h4>
          <p className="text-sm font-extrabold text-slate-800">{displayProvider}</p>
        </div>
      </div>

      {/* Connector 1: Provider -> Primary */}
      <div className="flex flex-col items-center my-1.5">
        <svg width="200" height="75" className="overflow-visible">
          <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
            <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
            </marker>
          </defs>
          <path d="M 100 0 L 100 65" stroke="url(#grad1)" strokeWidth="3" markerEnd="url(#arrow)" strokeDasharray="4 2" />
          <rect x="35" y="18" width="130" height="28" rx="6" fill="#eff6ff" stroke="#bfdbfe" strokeWidth="1" className="shadow-sm" />
          <text x="100" y="36" textAnchor="middle" fill="#1e3a8a" className="text-xs font-bold font-mono">
            Billed: {currencySymbol}{billed.toFixed(2)}
          </text>
        </svg>
      </div>

      {/* Node: Primary Insurer */}
      <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-xl border border-emerald-150 shadow-sm w-64 hover:translate-y-[-2px] transition-transform duration-200 ring-1 ring-emerald-500/10">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 text-lg shadow-sm">
          🛡️
        </div>
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Primary Insurer</h4>
          <p className="text-sm font-extrabold text-slate-800">{primaryInsurer || 'Primary Plan'}</p>
        </div>
      </div>

      {hasSecondary ? (
        <>
          {/* Connector 2: Primary -> Secondary */}
          <div className="flex flex-col items-center my-1.5">
            <svg width="200" height="75" className="overflow-visible">
              <defs>
                <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#6366f1" />
                </linearGradient>
                <marker id="arrow-indigo" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#6366f1" />
                </marker>
              </defs>
              <path d="M 100 0 L 100 65" stroke="url(#grad2)" strokeWidth="3" markerEnd="url(#arrow-indigo)" strokeDasharray="4 2" />
              <rect x="35" y="18" width="130" height="28" rx="6" fill="#f0fdf4" stroke="#bbf7d0" strokeWidth="1" className="shadow-sm" />
              <text x="100" y="36" textAnchor="middle" fill="#065f46" className="text-xs font-bold font-mono">
                Paid: {currencySymbol}{primaryPaid.toFixed(2)}
              </text>
            </svg>
          </div>

          {/* Node: Secondary Insurer */}
          <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-xl border border-indigo-150 shadow-sm w-64 hover:translate-y-[-2px] transition-transform duration-200 ring-1 ring-indigo-500/10">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 text-lg shadow-sm">
              🛡️
            </div>
            <div>
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">Secondary Insurer</h4>
              <p className="text-sm font-extrabold text-slate-800">{secondaryInsurer}</p>
            </div>
          </div>

          {/* Connector 3: Secondary -> Patient */}
          <div className="flex flex-col items-center my-1.5">
            <svg width="200" height="75" className="overflow-visible">
              <defs>
                <linearGradient id="grad3" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#6366f1" />
                  <stop offset="100%" stopColor="#f59e0b" />
                </linearGradient>
                <marker id="arrow-amber" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                </marker>
              </defs>
              <path d="M 100 0 L 100 65" stroke="url(#grad3)" strokeWidth="3" markerEnd="url(#arrow-amber)" strokeDasharray="4 2" />
              <rect x="35" y="18" width="130" height="28" rx="6" fill="#e0e7ff" stroke="#c7d2fe" strokeWidth="1" className="shadow-sm" />
              <text x="100" y="36" textAnchor="middle" fill="#3730a3" className="text-xs font-bold font-mono">
                Paid: {currencySymbol}{secondaryPaid.toFixed(2)}
              </text>
            </svg>
          </div>
        </>
      ) : (
        <>
          {/* Connector 2: Primary -> Patient directly */}
          <div className="flex flex-col items-center my-1.5">
            <svg width="200" height="75" className="overflow-visible">
              <defs>
                <linearGradient id="gradDirect" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#f59e0b" />
                </linearGradient>
                <marker id="arrow-amber-direct" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                </marker>
              </defs>
              <path d="M 100 0 L 100 65" stroke="url(#gradDirect)" strokeWidth="3" markerEnd="url(#arrow-amber-direct)" strokeDasharray="4 2" />
              <rect x="35" y="18" width="130" height="28" rx="6" fill="#f0fdf4" stroke="#bbf7d0" strokeWidth="1" className="shadow-sm" />
              <text x="100" y="36" textAnchor="middle" fill="#065f46" className="text-xs font-bold font-mono">
                Paid: {currencySymbol}{primaryPaid.toFixed(2)}
              </text>
            </svg>
          </div>
        </>
      )}

      {/* Node: Patient */}
      <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-xl border border-amber-150 shadow-sm w-64 hover:translate-y-[-2px] transition-transform duration-200 ring-1 ring-amber-500/10">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600 text-lg shadow-sm">
          👤
        </div>
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-amber-700">Patient Responsibility</h4>
          <p className="text-sm font-extrabold text-slate-800">Remaining: {currencySymbol}{patientOwes.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
};

// Expandable Pre-Auth Letters Panel
const PreAuthLettersPanel: React.FC<{ letters: any[]; preauthLettersMetadata?: any[] }> = ({ letters, preauthLettersMetadata }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0); // First letter open by default

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Generated Prior-Authorization Requests</h3>

      <div className="space-y-4">
        {letters.map((letter, i) => {
          const isExpanded = expandedIndex === i;
          const matchingMetadata = preauthLettersMetadata?.find(
            (meta: any) => meta.insurer_name === letter.insurer_name
          );
          const downloadUrl = matchingMetadata ? matchingMetadata.download_url : '';
          
          return (
            <div key={i} className="border border-slate-150 rounded-xl overflow-hidden shadow-sm transition-all duration-200">
              <button
                onClick={() => setExpandedIndex(isExpanded ? null : i)}
                className="w-full flex items-center justify-between bg-slate-50/40 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-800">{letter.insurer_name}</span>
                    <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 ring-1 ring-inset ring-emerald-600/10">
                      Drafted
                    </span>
                    {downloadUrl && (
                      <a
                        href={`http://127.0.0.1:8000${downloadUrl}`}
                        download
                        onClick={(e) => e.stopPropagation()}
                        className="ml-2 inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10.5px] font-extrabold text-blue-750 hover:bg-blue-100 transition-colors"
                      >
                        📥 Download PDF
                      </a>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-450 mt-1">Policy ID: {letter.policy_id} • Generated at: {new Date(letter.generated_at).toLocaleDateString()}</p>
                </div>
                <div>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={2.5}
                    stroke="currentColor"
                    className={`h-4 w-4 text-slate-400 transition-transform duration-250 ${isExpanded ? 'rotate-180' : ''}`}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </button>

              {isExpanded && (
                <div className="border-t border-slate-150 bg-slate-950 p-5 font-mono text-[11px] leading-relaxed text-slate-200 overflow-x-auto whitespace-pre-wrap max-h-72 overflow-y-auto scrollbar-thin">
                  {letter.letter_content}
                </div>
              )}
            </div>
          );
        })}
        {!letters.length && (
          <div className="text-center py-6 text-slate-400">No letters generated.</div>
        )}
      </div>
    </div>
  );
};


const getAgentIcon = (agentName: string): string => {
  const icons: Record<string, string> = {
    IntakeAgent: '📥',
    DocIntelAgent: '🔍',
    MedicalCodingAgent: '🏷️',
    InsuranceAgent: '🛡️',
    COBAgent: '🔀',
    FinanceAgent: '💵',
    ReviewerAgent: '⚖️',
  };
  return icons[agentName] || '🤖';
};

// Agent Workflow Visualization Node
const AgentPipelineVisualizer: React.FC<{ trace: any[] }> = ({ trace }) => {
  const steps = [
    { id: 'IntakeAgent', short: 'Intake', label: 'Intake', icon: '📥' },
    { id: 'DocIntelAgent', short: 'Doc Intel', label: 'Doc Intel', icon: '🔍' },
    { id: 'MedicalCodingAgent', short: 'Coding', label: 'Medical Coding', icon: '🏷️' },
    { id: 'InsuranceAgent', short: 'Insurance', label: 'Insurance', icon: '🛡️' },
    { id: 'COBAgent', short: 'COB', label: 'COB Engine', icon: '🔀' },
    { id: 'FinanceAgent', short: 'Finance', label: 'Finance Engine', icon: '💵' },
    { id: 'ReviewerAgent', short: 'Reviewer', label: 'Reviewer Auditor', icon: '⚖️' },
  ];

  return (
    <div className="bg-slate-50/50 rounded-2xl border border-slate-200/80 p-4 shadow-inner mb-6">
      <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3 text-center">
        Multi-Agent Adjudication Pipeline
      </h4>

      {/* Scrollable horizontal workflow row */}
      <div className="overflow-x-auto pb-1">
        <div className="flex items-center gap-1 min-w-max">
          {steps.map((step, idx) => {
            const matchingTrace = trace?.find((t) => t.agent_name === step.id);
            const status = matchingTrace ? matchingTrace.status : 'pending';

            let statusBg = 'bg-slate-100 border-slate-200 text-slate-400';
            let statusDot = 'bg-slate-400';

            if (status === 'success') {
              statusBg = 'bg-emerald-50 border-emerald-300 text-emerald-700 ring-1 ring-emerald-500/20';
              statusDot = 'bg-emerald-500 animate-pulse';
            } else if (status === 'warning') {
              statusBg = 'bg-amber-50 border-amber-300 text-amber-700 ring-1 ring-amber-500/20';
              statusDot = 'bg-amber-500';
            } else if (status === 'error') {
              statusBg = 'bg-rose-50 border-rose-300 text-rose-700 ring-1 ring-rose-500/20';
              statusDot = 'bg-rose-500';
            }

            return (
              <React.Fragment key={step.id}>
                {/* Connector between nodes */}
                {idx > 0 && (
                  <div className="flex items-center flex-shrink-0 w-5 h-[2px] bg-slate-200 relative">
                    {status !== 'pending' && (
                      <div className="absolute inset-0 bg-emerald-400/60 rounded-full" />
                    )}
                  </div>
                )}

                {/* Compact Node Card */}
                <div className={`flex flex-col items-center gap-1 px-2.5 py-2 rounded-lg border shadow-sm flex-shrink-0 transition-all hover:scale-[1.04] duration-200 ${statusBg}`} style={{ minWidth: '70px' }}>
                  <span className="text-base leading-none">{step.icon}</span>
                  <div className="text-center">
                    <div className="text-[9px] font-extrabold tracking-tight whitespace-nowrap">
                      {step.short}
                    </div>
                    <div className="flex items-center justify-center gap-1 mt-0.5">
                      <span className={`h-1 w-1 rounded-full flex-shrink-0 ${statusDot}`} />
                      <span className="text-[7px] font-bold uppercase tracking-wider opacity-70 whitespace-nowrap">
                        {status}
                      </span>
                    </div>
                  </div>
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// Main ResultsPage Component
export const ResultsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get('job_id');

  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [failedStep, setFailedStep] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const togglePlayAudio = () => {
    if (isPlayingAudio) {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      setIsPlayingAudio(false);
    } else {
      const audioUrl = report?.audio_summary?.download_url
        ? `http://127.0.0.1:8000${report.audio_summary.download_url}`
        : null;

      if (audioUrl) {
        if (!audioPlayerRef.current) {
          audioPlayerRef.current = new Audio(audioUrl);
        } else {
          audioPlayerRef.current.src = audioUrl;
        }

        audioPlayerRef.current.onended = () => setIsPlayingAudio(false);
        audioPlayerRef.current.onerror = () => {
          // Fallback to browser SpeechSynthesis if MP3 stream is unavailable
          if (report?.audio_briefing?.full_narration && 'speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(report.audio_briefing.full_narration);
            utterance.onend = () => setIsPlayingAudio(false);
            utterance.onerror = () => setIsPlayingAudio(false);
            window.speechSynthesis.speak(utterance);
          } else {
            setIsPlayingAudio(false);
          }
        };

        setIsPlayingAudio(true);
        audioPlayerRef.current.play().catch(() => {
          // Fallback if autoplay policy interrupts audio
          if (report?.audio_briefing?.full_narration && 'speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(report.audio_briefing.full_narration);
            utterance.onend = () => setIsPlayingAudio(false);
            utterance.onerror = () => setIsPlayingAudio(false);
            window.speechSynthesis.speak(utterance);
          } else {
            setIsPlayingAudio(false);
          }
        });
      } else if (report?.audio_briefing?.full_narration && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(report.audio_briefing.full_narration);
        utterance.onend = () => setIsPlayingAudio(false);
        utterance.onerror = () => setIsPlayingAudio(false);
        setIsPlayingAudio(true);
        window.speechSynthesis.speak(utterance);
      }
    }
  };

  useEffect(() => {
    return () => {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const fetchReport = useCallback(async () => {
    if (!jobId) {
      setError('No job ID provided. Please run an analysis first from the Intake Workspace.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setFailedStep(null);
    try {
      const data = await ApiService.getReportsSummary(jobId);
      setReport(data);
    } catch (err: any) {
      console.error('Failed to load reports summary:', err);
      const detail = err?.response?.data?.detail;
      if (detail && typeof detail === 'object') {
        setFailedStep(detail.step || null);
        setError(detail.message || 'Pipeline failed with an unknown error.');
      } else if (typeof detail === 'string') {
        setError(detail);
      } else if (err?.response?.status === 404) {
        setError('Analysis job not found. Please run the pipeline from the Intake Workspace.');
      } else if (err?.response?.status === 202) {
        setError('Analysis is still in progress. Please wait for completion and refresh.');
      } else {
        setError('Could not retrieve benefits report summary. Please verify that intake processing has been run.');
      }
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  const handleApprove = async () => {
    if (!jobId) return;
    try {
      setLoading(true);
      await ApiService.approveAnalysis(jobId);
      await fetchReport();
    } catch (err) {
      console.error('Failed to approve analysis:', err);
      alert('Failed to approve claim adjudication.');
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!jobId) return;
    try {
      setLoading(true);
      await ApiService.rejectAnalysis(jobId);
      // Wait for background job launch to register progress
      setTimeout(async () => {
        await fetchReport();
      }, 1500);
    } catch (err) {
      console.error('Failed to reject analysis:', err);
      alert('Failed to reject claim adjudication.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  if (loading) {
    return (
      <PageContainer className="max-w-xl py-24 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-50 text-blue-600 shadow-sm animate-pulse mb-4">
          <svg className="animate-spin h-7 w-7" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <h2 className="text-lg font-bold text-slate-800">Fetching Adjudication Results</h2>
        <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">Compiling Agent Audits & Estimates</p>
      </PageContainer>
    );
  }

  if (error || !report) {
    return (
      <PageContainer className="max-w-xl py-24 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-rose-50 text-rose-600 shadow-sm mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-6 w-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
        </div>
        <h2 className="text-lg font-bold text-slate-800">{failedStep ? 'Pipeline Failed' : 'Retrieval Failed'}</h2>
        {failedStep && (
          <div className="mt-2 inline-flex items-center rounded-full bg-rose-50 px-3 py-1 text-xs font-bold text-rose-700 ring-1 ring-inset ring-rose-600/10">
            Failed at: {failedStep}
          </div>
        )}
        <p className="text-sm text-slate-500 mt-3 px-6">{error}</p>
        <div className="mt-8 flex justify-center gap-4">
          <Link
            to="/intake"
            className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors"
          >
            Go to Intake Workspace
          </Link>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer className="max-w-7xl">
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-5 mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Benefits Coordination Results Dashboard</h1>
          <p className="text-sm text-slate-550 mt-1">
            Visualizing multi-agent adjudication pipeline, medical coding validations, and insurer details for patient:{' '}
            <strong className="text-slate-800">{report.patient_name}</strong>
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/intake"
            className="rounded-lg border border-slate-250 bg-white px-4.5 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
          >
            New Intake Run
          </Link>
        </div>
      </div>

      {/* Clinician Human-in-the-Loop Review Alert */}
      {report.requires_human_approval && !report.human_approved && (
        <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-6 mb-8 shadow-sm">
          <div className="flex gap-4 items-start">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-rose-100 text-rose-700 shadow-sm mt-0.5">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-5 w-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.008v.008H12v-.008Z" />
              </svg>
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-extrabold text-rose-900 uppercase tracking-wide">Clinician Audit Review Required</h4>
              <p className="text-xs text-rose-800 mt-1.5 leading-relaxed font-semibold">
                The Reviewer Agent has flagged low-confidence medical coding extraction on this claim. Clinical guidelines require manual clinician auditor review and sign-off before benefits are finalized.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleApprove}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition-colors cursor-pointer"
                >
                  Approve Claim Adjudication
                </button>
                <button
                  type="button"
                  onClick={handleReject}
                  className="rounded-lg border border-rose-200 bg-white px-4 py-2 text-xs font-bold text-rose-700 shadow-sm hover:bg-rose-50 transition-colors cursor-pointer"
                >
                  Reject & Request Re-extraction (Reflection)
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Clinician Approval Confirmation Banner */}
      {report.human_approved && (
        <div className="rounded-xl border border-emerald-250 bg-emerald-50/50 p-5 mb-8 shadow-sm">
          <div className="flex gap-3 items-center">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 shadow-inner">
              ✓
            </div>
            <div>
              <p className="text-xs font-bold text-emerald-900 leading-normal">
                Clinician Sign-off Completed: This claim has been audited and approved. Letters and audio briefings have been finalized.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Reviewer Warnings block */}
      {report.warnings && report.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 mb-8">
          <div className="flex gap-3">
            <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-700 mt-0.5">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-4 w-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.008v.008H12v-.008Z" />
              </svg>
            </div>
            <div>
              <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wide">Reviewer Warnings Detected</h4>
              <ul className="mt-1.5 space-y-1 list-disc pl-4 text-xs text-amber-800 leading-normal font-medium">
                {report.warnings.map((warning: string, idx: number) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Dashboard Main Grid Layout */}
      <div className="grid gap-8 lg:grid-cols-12 items-start">

        {/* Left Column (7/12 width) - Detailed visual panels */}
        <div className="lg:col-span-7 space-y-8">

          {/* Financial Breakdown Cards */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Financial Allocations Summary</h3>
            <div className="grid gap-4 sm:grid-cols-4">
              <div className="rounded-lg bg-slate-50 p-4 border border-slate-100 shadow-sm hover:scale-103 transition-transform duration-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Billed</span>
                <p className="text-xl font-extrabold text-slate-900 mt-1">
                  {report.financial_summary.currency === 'INR' ? '₹' : '$'}{report.financial_summary.total_billed.toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg bg-blue-50/50 p-4 border border-blue-100 shadow-sm hover:scale-103 transition-transform duration-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Primary Insurer Paid</span>
                <p className="text-xl font-extrabold text-blue-700 mt-1">
                  {report.financial_summary.currency === 'INR' ? '₹' : '$'}{report.financial_summary.primary_paid.toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg bg-indigo-50/50 p-4 border border-indigo-100 shadow-sm hover:scale-103 transition-transform duration-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">Secondary Insurer Paid</span>
                <p className="text-xl font-extrabold text-indigo-700 mt-1">
                  {report.financial_summary.currency === 'INR' ? '₹' : '$'}{report.financial_summary.secondary_paid.toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg bg-amber-50 p-4 border border-amber-150 shadow-sm hover:scale-103 transition-transform duration-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">Patient Responsibility</span>
                <p className="text-xl font-extrabold text-amber-850 mt-1">
                  {report.financial_summary.currency === 'INR' ? '₹' : '$'}{report.financial_summary.patient_responsibility.toFixed(2)}
                </p>
              </div>
            </div>
            {report.patient_claims?.length > 1 && (
              <div className="mt-5 border-t border-slate-100 pt-4">
                <p className="mb-3 text-[10px] font-bold uppercase tracking-wider text-slate-400">Patient-specific claims</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {report.patient_claims.map((claim: any) => (
                    <div key={claim.member_id} className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs font-extrabold text-slate-800">{claim.patient_name}</p>
                          <p className="text-[10px] text-slate-500">Member {claim.member_id}</p>
                        </div>
                        <p className="text-sm font-extrabold text-amber-800">
                          ₹{claim.total_patient_responsibility.toFixed(2)} due
                        </p>
                      </div>
                      <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
                        Billed ₹{claim.total_billed.toFixed(2)} · Primary {claim.primary_policy_id || 'unresolved'} · Secondary {claim.secondary_policy_id || 'none'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Per-Procedure Coverage Decision Breakdown */}
          {report.cob_lines && report.cob_lines.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-1">Coverage Decision Breakdown</h3>
              <p className="text-[11px] text-slate-450 mb-4">Per-procedure adjudication showing exactly which procedures were covered or denied by each insurer and why.</p>
              
              <div className="space-y-3">
                {report.cob_lines.map((line: any, idx: number) => {
                  const currSym = report.financial_summary.currency === 'INR' ? '₹' : '$';
                  const allDenied = !line.is_primary_covered && !line.is_secondary_covered;
                  const partialDenied = line.is_primary_covered && !line.is_secondary_covered && line.secondary_paid === 0;
                  
                  let borderColor = 'border-emerald-200';
                  let bgColor = 'bg-emerald-50/30';
                  let statusIcon = '✅';
                  let statusText = 'Covered';
                  let statusColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';
                  
                  if (allDenied) {
                    borderColor = 'border-rose-200';
                    bgColor = 'bg-rose-50/30';
                    statusIcon = '❌';
                    statusText = 'Not Covered';
                    statusColor = 'text-rose-700 bg-rose-50 border-rose-200';
                  } else if (partialDenied) {
                    borderColor = 'border-amber-200';
                    bgColor = 'bg-amber-50/20';
                    statusIcon = '⚠️';
                    statusText = 'Partial';
                    statusColor = 'text-amber-700 bg-amber-50 border-amber-200';
                  }
                  
                  return (
                    <div key={idx} className={`rounded-xl border ${borderColor} ${bgColor} p-4 transition-all hover:shadow-sm`}>
                      {/* Header row */}
                       <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-700 ring-1 ring-inset ring-slate-300/50 font-mono shrink-0">
                            {line.cpt_code}
                          </span>
                          {line.description && (
                            <span className="text-[11.5px] font-bold text-slate-700 truncate max-w-[200px] sm:max-w-[320px] md:max-w-[400px]" title={line.description}>
                              {line.description}
                            </span>
                          )}
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold border shrink-0 ${statusColor}`}>
                            {statusIcon} {statusText}
                          </span>
                        </div>
                         <span className="text-sm font-extrabold text-slate-800">{currSym}{line.billed_amount.toFixed(2)}</span>
                       </div>
                       {(line.patient_name || line.source_document) && (
                         <div className="mb-3 flex flex-wrap gap-2 text-[10px] font-semibold text-slate-500">
                           {line.patient_name && (
                             <span className="rounded-full border border-slate-200 bg-white px-2 py-1">
                               Patient: {line.patient_name}{line.member_id ? ` (${line.member_id})` : ''}
                             </span>
                           )}
                           {line.source_document && (
                             <span className="rounded-full border border-slate-200 bg-white px-2 py-1">
                               Charge source: {line.source_document.replaceAll('_', ' ')}
                             </span>
                           )}
                         </div>
                       )}
                      
                      {/* Payment details grid */}
                      <div className="grid grid-cols-3 gap-3 text-xs">
                        {/* Primary */}
                        <div className={`rounded-lg p-2.5 ${line.is_primary_covered ? 'bg-blue-50/60 border border-blue-100' : 'bg-slate-50 border border-slate-150'}`}>
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className={`h-1.5 w-1.5 rounded-full ${line.is_primary_covered ? 'bg-blue-500' : 'bg-slate-300'}`} />
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Primary</span>
                          </div>
                          <p className={`text-sm font-extrabold ${line.is_primary_covered ? 'text-blue-700' : 'text-slate-400'}`}>
                            {line.is_primary_covered ? `${currSym}${line.primary_paid.toFixed(2)}` : 'Not Covered'}
                          </p>
                          {line.is_primary_covered && (line.primary_deductible > 0 || line.primary_coinsurance > 0) && (
                            <p className="text-[10px] text-slate-450 mt-0.5">
                              {line.primary_deductible > 0 && `Ded: ${currSym}${line.primary_deductible.toFixed(0)}`}
                              {line.primary_deductible > 0 && line.primary_coinsurance > 0 && ' • '}
                              {line.primary_coinsurance > 0 && `Coins: ${currSym}${line.primary_coinsurance.toFixed(0)}`}
                            </p>
                          )}
                        </div>
                        
                        {/* Secondary */}
                        <div className={`rounded-lg p-2.5 ${line.is_secondary_covered ? 'bg-indigo-50/60 border border-indigo-100' : 'bg-slate-50 border border-slate-150'}`}>
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className={`h-1.5 w-1.5 rounded-full ${line.is_secondary_covered ? 'bg-indigo-500' : 'bg-slate-300'}`} />
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Secondary</span>
                          </div>
                          <p className={`text-sm font-extrabold ${line.is_secondary_covered ? 'text-indigo-700' : 'text-slate-400'}`}>
                            {line.is_secondary_covered ? `${currSym}${line.secondary_paid.toFixed(2)}` : 'Not Covered'}
                          </p>
                          {line.is_secondary_covered && line.secondary_deductible > 0 && (
                            <p className="text-[10px] text-slate-450 mt-0.5">Ded credited: {currSym}{line.secondary_deductible.toFixed(0)}</p>
                          )}
                        </div>
                        
                        {/* Patient */}
                        <div className={`rounded-lg p-2.5 ${allDenied ? 'bg-rose-50/60 border border-rose-150' : 'bg-amber-50/60 border border-amber-100'}`}>
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className={`h-1.5 w-1.5 rounded-full ${allDenied ? 'bg-rose-500' : 'bg-amber-500'}`} />
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Patient</span>
                          </div>
                          <p className={`text-sm font-extrabold ${allDenied ? 'text-rose-700' : 'text-amber-800'}`}>
                            {currSym}{line.patient_responsibility.toFixed(2)}
                          </p>
                          {allDenied && (
                            <p className="text-[10px] text-rose-600 font-semibold mt-0.5">Full amount owed</p>
                          )}
                        </div>
                      </div>
                      
                      {/* Notes / denial reason */}
                      {line.notes && (
                        <div className={`mt-2.5 rounded-lg px-3 py-2 text-[11px] leading-relaxed font-medium ${
                          allDenied 
                            ? 'bg-rose-50 text-rose-800 border border-rose-150' 
                            : 'bg-slate-50/80 text-slate-600 border border-slate-100'
                        }`}>
                          {allDenied && <span className="font-bold text-rose-700">⛔ Denial Reason: </span>}
                          {line.notes}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              
              {/* Summary footer for denied procedures */}
              {report.cob_lines.some((l: any) => !l.is_primary_covered) && (
                <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50/40 p-4">
                  <div className="flex items-start gap-2.5">
                    <span className="text-base mt-0.5">🚫</span>
                    <div>
                      <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wide">Coverage Denial Summary</h4>
                      <p className="text-[11px] text-rose-800 mt-1 leading-relaxed">
                        {report.cob_lines.filter((l: any) => !l.is_primary_covered).length} of {report.cob_lines.length} procedure(s) were 
                        <strong> not covered</strong> by the primary insurer. This may be because the uploaded documents contained procedures 
                        that are excluded from your policy, or the extracted CPT codes do not match any covered services. 
                        Review the denial reasons above and contact your insurer for appeals if needed.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Cost Flow Visual Path */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Adjudicated Claims Cost Flow</h3>
              {jobId && (
                <a
                  href={`http://127.0.0.1:8000/api/v1/reports/download/cost_flow.svg?job_id=${jobId}`}
                  download="dual_coverage_cost_flow.svg"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700 hover:bg-slate-100 hover:text-blue-650 transition-colors shadow-sm"
                >
                  📊 Download SVG Waterfall
                </a>
              )}
            </div>
            <CostFlowVisualizer
              billed={report.financial_summary.total_billed}
              primaryPaid={report.financial_summary.primary_paid}
              secondaryPaid={report.financial_summary.secondary_paid}
              patientOwes={report.financial_summary.patient_responsibility}
              primaryInsurer={report.financial_summary.primary_provider || 'Primary Insurer'}
              secondaryInsurer={report.financial_summary.secondary_provider || ''}
              currencySymbol={report.financial_summary.currency === 'INR' ? '₹' : '$'}
              providerName={report.cob_lines?.[0]?.source_document ? undefined : undefined}
            />
          </div>

          {/* Medical Coding Table */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Medical Coding Inference</h3>

            <div className="space-y-6">
              <div>
                <h4 className="text-xs font-bold text-slate-500 mb-2.5 uppercase tracking-wide">Diagnosis (ICD-10-CM)</h4>
                <div className="overflow-hidden border border-slate-150 rounded-xl">
                  <table className="min-w-full divide-y divide-slate-150 text-left text-xs">
                    <thead className="bg-slate-50/80 font-semibold text-slate-600">
                      <tr>
                        <th className="px-4 py-3">Code</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3 text-right">AI Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-800">
                      {report.coding_result?.diagnoses?.map((diag: any, i: number) => (
                        <tr key={i} className="hover:bg-slate-50/30">
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-700 ring-1 ring-inset ring-blue-700/10 font-mono">
                              {diag.code}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-700">{diag.description}</td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="h-1.5 w-16 rounded-full bg-slate-100 overflow-hidden">
                                <div className="h-full bg-emerald-500 rounded-full animate-pulse-slow" style={{ width: `${diag.confidence * 100}%` }} />
                              </div>
                              <span className="font-mono font-bold text-slate-550">{(diag.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {(!report.coding_result?.diagnoses || !report.coding_result.diagnoses.length) && (
                        <tr>
                          <td colSpan={3} className="px-4 py-6 text-center text-slate-400">No diagnosis codes found.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-slate-500 mb-2.5 uppercase tracking-wide">Procedure (CPT)</h4>
                <div className="overflow-hidden border border-slate-150 rounded-xl">
                  <table className="min-w-full divide-y divide-slate-150 text-left text-xs">
                    <thead className="bg-slate-50/80 font-semibold text-slate-600">
                      <tr>
                        <th className="px-4 py-3">Code</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3 text-right">AI Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-800">
                      {report.coding_result?.procedures?.map((proc: any, i: number) => (
                        <tr key={i} className="hover:bg-slate-50/30">
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-bold text-indigo-700 ring-1 ring-inset ring-indigo-700/10 font-mono">
                              {proc.code}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-700">{proc.description}</td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="h-1.5 w-16 rounded-full bg-slate-100 overflow-hidden">
                                <div className="h-full bg-emerald-500 rounded-full animate-pulse-slow" style={{ width: `${proc.confidence * 100}%` }} />
                              </div>
                              <span className="font-mono font-bold text-slate-550">{(proc.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {(!report.coding_result?.procedures || !report.coding_result.procedures.length) && (
                        <tr>
                          <td colSpan={3} className="px-4 py-6 text-center text-slate-400">No procedure codes found.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          {/* Pre-Authorization Letters */}
          <PreAuthLettersPanel letters={report.letters} preauthLettersMetadata={report.preauth_letters} />

        </div>

        {/* Right Column (5/12 width) - Timeline & pipeline tracking */}
        <div className="lg:col-span-5 space-y-8">

          {/* Workflow Summary Checklist */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Adjudication Progress Timeline</h3>

            <div className="space-y-3.5">
              {Object.entries(report.workflow_summary || {}).map(([step, completed], i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                    completed 
                      ? 'bg-emerald-50 border-emerald-500 text-emerald-600 shadow-sm' 
                      : 'border-slate-200 text-slate-300'
                  }`}>
                    {completed ? (
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor" className="h-3 w-3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                    ) : (
                      <div className="h-1.5 w-1.5 rounded-full bg-slate-350" />
                    )}
                  </div>
                  <span className={`text-xs font-semibold ${completed ? 'text-slate-800 font-bold' : 'text-slate-400'}`}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Workflow Trace Timeline */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Agent Execution Trace Log</h3>

            {/* Visual Pipeline */}
            <AgentPipelineVisualizer trace={report.trace} />

            <div className="relative border-l border-slate-150 pl-5 ml-2.5 space-y-5 text-xs">
              {report.trace?.map((entry: any, i: number) => {
                const icon = getAgentIcon(entry.agent_name);

                let cardBorder = 'border-slate-100 bg-slate-50/40';
                let statusBadge = 'bg-emerald-50 text-emerald-700 border-emerald-200';

                if (entry.status === 'warning') {
                  cardBorder = 'border-amber-150 bg-amber-50/10';
                  statusBadge = 'bg-amber-50 text-amber-700 border-amber-200';
                } else if (entry.status === 'error') {
                  cardBorder = 'border-rose-150 bg-rose-50/10';
                  statusBadge = 'bg-rose-55 text-rose-700 border-rose-200';
                }

                return (
                  <div key={i} className="relative">
                    {/* Timeline bullet marker */}
                    <div className="absolute -left-7.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm ring-4 ring-white">
                      <span className="text-[10px]">{icon}</span>
                    </div>

                    <div className={`space-y-1.5 border rounded-xl p-3.5 shadow-sm hover:scale-[1.01] hover:shadow-md transition-all duration-200 ${cardBorder}`}>
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-extrabold text-slate-800 text-sm">
                            {entry.agent_name}
                          </span>
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-bold border uppercase tracking-wider ${statusBadge}`}>
                            {entry.status}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono font-semibold flex items-center gap-2">
                          <span>
                            {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                        </div>
                      </div>

                      <p className="text-slate-550 leading-relaxed font-medium text-[11px] mt-1.5">
                        {entry.message}
                      </p>
                    </div>
                  </div>
                );
              })}
              {(!report.trace || !report.trace.length) && (
                <div className="text-center py-6 text-slate-400">No agent trace logs recorded.</div>
              )}
            </div>
          </div>

          {/* Audio stream briefings summary briefing streamer card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Briefing Audio Streamer</h3>

            <div className="rounded-xl border border-slate-150 p-4.5 bg-slate-50/50 text-center shadow-sm">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-blue-50 text-blue-600 mb-2.5 shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-5.5 w-5.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
                </svg>
              </div>
              <span className="text-xs font-bold text-slate-800">TTS Audio Adjudication Briefing</span>
              <p className="text-[10px] text-slate-400 mt-1.5 font-semibold">Duration: {report.audio_briefing?.estimated_duration_seconds}s</p>

              <button
                type="button"
                onClick={togglePlayAudio}
                className={`mt-3.5 rounded-lg border px-4 py-1.5 text-xs font-bold transition-colors w-full cursor-pointer ${
                  isPlayingAudio
                    ? 'border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                {isPlayingAudio ? '⏹️ Stop Audio Briefing' : '🔊 Play Audio Briefing'}
              </button>
              {report.audio_summary?.download_url && (
                <a
                  href={`http://127.0.0.1:8000${report.audio_summary.download_url}`}
                  download
                  className="mt-2.5 block text-center rounded-lg border border-slate-200 bg-slate-100 px-4 py-1.5 text-[10.5px] font-extrabold text-slate-600 hover:bg-slate-200 hover:text-slate-700 transition-colors w-full cursor-pointer"
                >
                  📥 Download Audio Briefing (MP3)
                </a>
              )}
            </div>

            {/* Patient Briefing Narration Script */}
            {report.audio_briefing && (
              <div className="mt-6 border-t border-slate-150 pt-5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-450 mb-3 flex items-center justify-between">
                  <span>Patient Briefing Script</span>
                  <span className="text-[9px] font-semibold text-emerald-650 bg-emerald-50 px-1.5 py-0.5 rounded">TTS Enabled</span></h4>
                <div className="space-y-3.5 text-xs">
                  {report.audio_briefing.sections.map((section: any, idx: number) => (
                    <div key={idx} className="bg-slate-50/50 rounded-xl p-3 border border-slate-100">
                      <span className="font-extrabold text-slate-700 block text-[10px] uppercase tracking-wide mb-1">
                        {section.title}
                      </span>
                      <p className="text-slate-600 leading-relaxed font-medium">{section.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </PageContainer>
  );
};
