import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { RequirementSlotCard } from '../../components/intake/RequirementSlotCard';
import type { RequirementSlot, RequirementSlotId, UploadedFile } from '../../types/intake';
import { ApiService } from '../../services/api';

// ─── Agent metadata ──────────────────────────────────────────────────────────
const AGENT_META: Record<string, { emoji: string; label: string; description: string }> = {
    IntakeAgent: { emoji: '📋', label: 'Intake Agent', description: 'Verifying uploaded documents in storage slots' },
    DocIntelAgent: { emoji: '🔍', label: 'Doc Intel Agent', description: 'Extracting text via OCR from all uploaded files' },
    MedicalCodingAgent: { emoji: '🧬', label: 'Medical Coding Agent', description: 'Inferring ICD-10 and CPT codes with Gemini AI' },
    InsuranceAgent: { emoji: '🏥', label: 'Insurance Agent', description: 'Resolving insurance policies for this patient' },
    COBAgent: { emoji: '⚖️', label: 'COB Agent', description: 'Coordinating benefits across primary & secondary plans' },
    FinanceAgent: { emoji: '💰', label: 'Finance Agent', description: 'Computing audited financial breakdown & deductibles' },
    ReviewerAgent: { emoji: '🔎', label: 'Reviewer Agent', description: 'Quality auditing pipeline outputs and confidence scores' },
    ClinicianAuditor: { emoji: '👨‍⚕️', label: 'Clinician Auditor', description: 'Manual clinical sign-off' },
};

interface AgentFeedEntry {
    agentName: string;
    status: 'running' | 'success' | 'retry' | 'error';
    message: string;
    timestamp: string;
}

export const IntakePage: React.FC = () => {
    const navigate = useNavigate();

    const requirementSlots: RequirementSlot[] = [
        { id: 'priya_pt_invoice', title: 'Priya PT Invoice', description: 'Physical therapy invoice with billing codes, sessions, and amounts.', allowedFormats: ['.pdf', '.png', '.jpg', '.jpeg'] },
        { id: 'aarav_mri_report', title: 'Aarav MRI Report', description: 'Radiology MRI report highlighting medical findings.', allowedFormats: ['.pdf', '.png', '.jpg', '.jpeg'] },
        { id: 'surgeon_estimate', title: 'Surgeon Estimate', description: 'Fee estimate with procedure codes, facility costs, and pricing.', allowedFormats: ['.pdf', '.png', '.jpg', '.jpeg'] },
        { id: 'user_query_transcript', title: 'User Query Transcript', description: 'Text transcript containing the benefit coordination query.', allowedFormats: ['.txt', '.pdf'] },
    ];

    const [uploadedFiles, setUploadedFiles] = useState<Record<RequirementSlotId, UploadedFile | undefined>>({
        priya_pt_invoice: undefined, aarav_mri_report: undefined,
        surgeon_estimate: undefined, user_query_transcript: undefined,
    });
    const [analysisStatus, setAnalysisStatus] = useState<'idle' | 'starting' | 'processing' | 'awaiting_approval' | 'completed' | 'failed'>('idle');
    const [progress, setProgress] = useState(0);
    const [phaseMessage, setPhaseMessage] = useState('');
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [failedAgent, setFailedAgent] = useState<string | null>(null);
    const [ocrEngine, setOcrEngine] = useState<'library' | 'gemini'>('library');
    const [mockMode, setMockMode] = useState(true);
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const [currentAgent, setCurrentAgent] = useState<string | null>(null);
    const [agentFeed, setAgentFeed] = useState<AgentFeedEntry[]>([]);
    const [reviewWarnings, setReviewWarnings] = useState<string[]>([]);
    const feedBottomRef = useRef<HTMLDivElement>(null);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Fetch existing uploads on mount — sync only what's already on the backend (no auto-populate)
    useEffect(() => {
        ApiService.fetchIntakeStatus().then(setUploadedFiles).catch(() => { });
    }, []);

    // Auto-scroll agent feed
    useEffect(() => {
        feedBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [agentFeed, currentAgent]);

    const handleUpload = async (file: File, slotId: RequirementSlotId) => {
        setUploadedFiles(prev => ({ ...prev, [slotId]: { name: file.name, size: file.size, type: file.type, status: 'uploading', slotId } }));
        try {
            const uploaded = await ApiService.uploadDocument(file, slotId);
            setUploadedFiles(prev => ({ ...prev, [slotId]: uploaded }));
        } catch (err: any) {
            let errorMsg = 'Upload failed. Check your network connection.';
            if (axios.isAxiosError(err) && err.response) errorMsg = err.response.data?.detail || `Server error ${err.response.status}`;
            else if (axios.isAxiosError(err) && err.request) errorMsg = 'No response from backend server.';
            setUploadedFiles(prev => ({ ...prev, [slotId]: { name: file.name, size: file.size, type: file.type, status: 'error', slotId, errorMsg } }));
        }
    };

    const handleRemove = async (slotId: RequirementSlotId) => {
        setUploadedFiles(prev => ({ ...prev, [slotId]: undefined }));
        try { await ApiService.deleteDocument(slotId); } catch { /* silent */ }
    };

    const addFeedEntry = (entry: AgentFeedEntry) => {
        setAgentFeed(prev => {
            const filtered = prev.filter(e => !(e.agentName === entry.agentName && e.status === 'running'));
            return [...filtered, entry];
        });
    };

    const buildPollingLoop = (job_id: string, seenAgents: Set<string>) => {
        return setInterval(async () => {
            try {
                const res = await ApiService.getAnalysisStatus(job_id);
                const { status: jobStatus, progress_percent, message, error_details, current_agent: activeAgent, warnings } = res;

                setProgress(progress_percent);
                setPhaseMessage(message);
                if (activeAgent !== undefined) setCurrentAgent(activeAgent ?? null);

                // Detect completed agents from message
                const completedMatch = Object.keys(AGENT_META).find(
                    name => message.includes(name + ':') && !seenAgents.has(name)
                );
                if (completedMatch) {
                    seenAgents.add(completedMatch);
                    const isRetry = message.toLowerCase().includes('retry') || message.toLowerCase().includes('backtrack');
                    const isError = message.toLowerCase().includes('failed') || message.toLowerCase().includes('error');
                    addFeedEntry({ agentName: completedMatch, status: isError ? 'error' : isRetry ? 'retry' : 'success', message, timestamp: new Date().toLocaleTimeString() });
                    setCurrentAgent(null);
                }

                if (jobStatus === 'completed') {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    setCurrentAgent(null);
                    setAnalysisStatus('completed');
                    setTimeout(() => navigate(`/results?job_id=${job_id}`), 600);
                } else if (jobStatus === 'awaiting_approval') {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    setCurrentAgent(null);
                    setReviewWarnings(warnings || []);
                    setAnalysisStatus('awaiting_approval');
                } else if (jobStatus === 'failed') {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    setCurrentAgent(null);
                    setAnalysisStatus('failed');
                    setErrorMessage(message || error_details || 'Pipeline failed.');
                }
            } catch {
                if (intervalRef.current) clearInterval(intervalRef.current);
                setAnalysisStatus('failed');
                setErrorMessage('Lost connection to backend while polling. Please retry.');
            }
        }, 1200);
    };

    const startAssessment = async () => {
        setAnalysisStatus('starting');
        setProgress(5);
        setAgentFeed([]);
        setCurrentAgent(null);
        setReviewWarnings([]);
        setPhaseMessage('Contacting backend orchestrator...');
        try {
            const { job_id } = await ApiService.startAnalysis(ocrEngine, mockMode);
            setActiveJobId(job_id);
            setAnalysisStatus('processing');
            intervalRef.current = buildPollingLoop(job_id, new Set<string>());
        } catch (err: any) {
            setAnalysisStatus('failed');
            const detail = err?.response?.data?.detail;
            setErrorMessage(typeof detail === 'string' ? detail : 'Backend is not responding. Ensure it is running on port 8000.');
        }
    };

    const resetWorkspace = async () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
        for (const slotId of Object.keys(uploadedFiles) as RequirementSlotId[]) {
            if (uploadedFiles[slotId]) try { await ApiService.deleteDocument(slotId); } catch { /* silent */ }
        }
        setUploadedFiles({ priya_pt_invoice: undefined, aarav_mri_report: undefined, surgeon_estimate: undefined, user_query_transcript: undefined });
        setAnalysisStatus('idle');
        setProgress(0);
        setPhaseMessage('');
        setAgentFeed([]);
        setCurrentAgent(null);
        setReviewWarnings([]);
    };

    const getAgentState = (agentName: string): 'pending' | 'running' | 'success' | 'retry' | 'error' => {
        if (analysisStatus === 'failed' && currentAgent === agentName) {
            return 'error';
        }
        
        const feedEntry = agentFeed.find(entry => entry.agentName === agentName);
        if (feedEntry) {
            if (feedEntry.status === 'error') return 'error';
            if (feedEntry.status === 'retry' && currentAgent !== agentName) return 'retry';
            if (feedEntry.status === 'success' && currentAgent !== agentName) return 'success';
        }

        if (currentAgent === agentName) {
            return 'running';
        }

        const milestones: Record<string, number> = {
            IntakeAgent: 15,
            DocIntelAgent: 35,
            MedicalCodingAgent: 55,
            InsuranceAgent: 70,
            COBAgent: 85,
            FinanceAgent: 95,
            ReviewerAgent: 100,
        };

        if (agentName === 'ClinicianAuditor') {
            if (analysisStatus === 'awaiting_approval') return 'running';
            if (progress === 100 && analysisStatus === 'completed') return 'success';
            return 'pending';
        }

        const milestone = milestones[agentName];
        if (milestone && progress >= milestone) {
            return 'success';
        }

        return 'pending';
    };

    const activeFiles = Object.values(uploadedFiles).filter(f => f?.status === 'ready') as UploadedFile[];
    const isAllUploaded = requirementSlots.every(s => uploadedFiles[s.id]?.status === 'ready');
    const isNoneUploaded = activeFiles.length === 0;

    // ── FAILED ──────────────────────────────────────────────────────────────
    if (analysisStatus === 'failed') {
        return (
            <PageContainer className="max-w-xl py-16">
                <div style={{ borderRadius: 20, border: '1px solid #fecaca', background: '#fff', padding: 32, textAlign: 'center', boxShadow: '0 2px 16px rgba(0,0,0,0.06)' }}>
                    <div style={{ margin: '0 auto', width: 64, height: 64, borderRadius: '50%', background: '#fef2f2', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28 }}>❌</div>
                    <h2 style={{ marginTop: 20, fontSize: 20, fontWeight: 700, color: '#111', margin: '16px 0 4px' }}>Pipeline Failed</h2>
                    <p style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 12px' }}>Multi-Agent Orchestration Error</p>
                    {failedAgent && (
                        <div style={{ display: 'inline-block', background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 20, padding: '3px 12px', fontSize: 11, fontWeight: 700, color: '#b91c1c', marginBottom: 12 }}>
                            Failed at: {failedAgent}
                        </div>
                    )}
                    <p style={{ fontSize: 13, fontWeight: 500, color: '#dc2626', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 12, padding: '14px 20px', margin: '0 0 20px' }}>
                        {errorMessage || 'An unknown error occurred during pipeline execution.'}
                    </p>
                    <button onClick={() => { setAnalysisStatus('idle'); setProgress(0); setPhaseMessage(''); setErrorMessage(null); setFailedAgent(null); setAgentFeed([]); setCurrentAgent(null); }}
                        style={{ borderRadius: 8, background: '#2563eb', color: '#fff', border: 'none', padding: '8px 18px', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                        Retry Assessment
                    </button>
                </div>
            </PageContainer>
        );
    }

    // ── PROCESSING / AWAITING APPROVAL ──────────────────────────────────────
    if (analysisStatus === 'starting' || analysisStatus === 'processing' || analysisStatus === 'awaiting_approval') {
        const isApproval = analysisStatus === 'awaiting_approval';
        return (
            <PageContainer className="max-w-2xl py-10">
                <div style={{ borderRadius: 20, border: `1px solid ${isApproval ? '#fde68a' : '#e2e8f0'}`, background: '#fff', padding: '28px 32px', boxShadow: '0 2px 16px rgba(0,0,0,0.06)' }}>

                    {/* Header */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
                        <div style={{ width: 48, height: 48, borderRadius: '50%', background: isApproval ? '#fef3c7' : '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, flexShrink: 0 }}>
                            {isApproval ? '⚠️' : (
                                <svg style={{ width: 24, height: 24, color: '#2563eb', animation: 'spin 1s linear infinite' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                            )}
                        </div>
                        <div>
                            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', margin: 0 }}>
                                {isApproval ? 'Clinician Sign-off Required' : 'Analyzing Benefits'}
                            </h2>
                            <p style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', margin: '2px 0 0' }}>
                                {isApproval ? 'Reviewer Agent Flagged Issues — Action Required' : 'Orchestrating AI Agents via Google ADK'}
                            </p>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div style={{ marginBottom: 20 }}>
                        <div style={{ height: 8, borderRadius: 99, background: '#f1f5f9', overflow: 'hidden' }}>
                            <div style={{ height: '100%', borderRadius: 99, transition: 'width 0.7s ease', width: `${progress}%`, background: isApproval ? '#f59e0b' : 'linear-gradient(90deg, #3b82f6, #6366f1)' }} />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                            <span>Progress</span><span>{progress}%</span>
                        </div>
                    </div>

                    {/* Agent Stepper Pipeline */}
                    <div style={{ marginBottom: 24 }}>
                        <h3 style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
                            Active Specialist Agents Pipeline
                        </h3>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10 }}>
                            {Object.entries(AGENT_META).map(([name, meta]) => {
                                const state = getAgentState(name);
                                
                                let bg = '#f8fafc';
                                let border = '1px solid #e2e8f0';
                                let iconColor = '#94a3b8';
                                let labelColor = '#64748b';
                                let statusText = 'Pending';
                                let glowStyle = {};
                                let pulseDot = null;
                                
                                if (state === 'running') {
                                    bg = '#eff6ff';
                                    border = '1px solid #3b82f6';
                                    iconColor = '#3b82f6';
                                    labelColor = '#1e40af';
                                    statusText = 'Active';
                                    glowStyle = {
                                        boxShadow: '0 0 14px rgba(59, 130, 246, 0.25)',
                                        animation: 'pulse 1.8s infinite ease-in-out'
                                    };
                                    pulseDot = <span style={{ position: 'absolute', top: 6, right: 6, display: 'block', height: 8, width: 8, borderRadius: '50%', background: '#2563eb' }} />;
                                } else if (state === 'success') {
                                    bg = '#f0fdf4';
                                    border = '1px solid #bcf0da';
                                    iconColor = '#16a34a';
                                    labelColor = '#14532d';
                                    statusText = 'Completed';
                                } else if (state === 'retry') {
                                    bg = '#fffbeb';
                                    border = '1px solid #fde68a';
                                    iconColor = '#d97706';
                                    labelColor = '#78350f';
                                    statusText = 'Retrying';
                                } else if (state === 'error') {
                                    bg = '#fef2f2';
                                    border = '1px solid #fca5a5';
                                    iconColor = '#dc2626';
                                    labelColor = '#7f1d1d';
                                    statusText = 'Failed';
                                }
                                
                                return (
                                    <div
                                        key={name}
                                        style={{
                                            borderRadius: 12,
                                            background: bg,
                                            border: border,
                                            padding: '12px 8px',
                                            display: 'flex',
                                            flexDirection: 'column',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            textAlign: 'center',
                                            position: 'relative',
                                            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                            ...glowStyle
                                        }}
                                    >
                                        {pulseDot}
                                        <div style={{ fontSize: 20, marginBottom: 4 }}>{meta.emoji}</div>
                                        <div style={{ fontSize: 11, fontWeight: 700, color: labelColor, lineHeight: 1.2, whiteSpace: 'nowrap' }}>
                                            {meta.label}
                                        </div>
                                        <div style={{ fontSize: 8, fontWeight: 700, color: iconColor, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>
                                            {statusText}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Live Agent Feed */}
                    <div style={{ borderRadius: 12, border: '1px solid #e2e8f0', background: '#f8fafc', overflow: 'hidden', marginBottom: 16 }}>
                        <div style={{ padding: '8px 14px', borderBottom: '1px solid #e2e8f0', fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                            Live Agent Feed
                        </div>
                        <div style={{ maxHeight: 240, overflowY: 'auto', padding: '4px 0' }}>
                            {agentFeed.length === 0 && !currentAgent && (
                                <div style={{ padding: '12px 16px', fontSize: 12, color: '#94a3b8', fontStyle: 'italic' }}>Waiting for first agent to start...</div>
                            )}
                            {agentFeed.map((entry, i) => {
                                const meta = AGENT_META[entry.agentName] || { emoji: '🤖', label: entry.agentName, description: '' };
                                const clr = entry.status === 'success' ? '#16a34a' : entry.status === 'retry' ? '#d97706' : '#dc2626';
                                const bg = entry.status === 'success' ? '#f0fdf4' : entry.status === 'retry' ? '#fffbeb' : '#fef2f2';
                                const badge = entry.status === 'success' ? '✅ Done' : entry.status === 'retry' ? '🔄 Retried' : '❌ Error';
                                return (
                                    <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 14px', borderBottom: '1px solid #f1f5f9' }}>
                                        <span style={{ fontSize: 16, flexShrink: 0, marginTop: 2 }}>{meta.emoji}</span>
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                                                <span style={{ fontSize: 12, fontWeight: 700, color: '#1e293b' }}>{meta.label}</span>
                                                <span style={{ fontSize: 10, fontWeight: 700, color: clr, background: bg, border: `1px solid ${clr}33`, borderRadius: 20, padding: '1px 7px', flexShrink: 0 }}>{badge}</span>
                                                <span style={{ fontSize: 10, color: '#94a3b8', marginLeft: 'auto' }}>{entry.timestamp}</span>
                                            </div>
                                            <p style={{ fontSize: 11, color: '#475569', margin: '3px 0 0', lineHeight: 1.5, wordBreak: 'break-word' }}>{entry.message}</p>
                                        </div>
                                    </div>
                                );
                            })}
                            {currentAgent && !isApproval && (
                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 14px', background: '#eff6ff' }}>
                                    <span style={{ fontSize: 16, flexShrink: 0, marginTop: 2 }}>{AGENT_META[currentAgent]?.emoji || '🤖'}</span>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                            <span style={{ fontSize: 12, fontWeight: 700, color: '#1e40af' }}>{AGENT_META[currentAgent]?.label || currentAgent}</span>
                                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10, fontWeight: 700, color: '#2563eb', background: '#dbeafe', border: '1px solid #bfdbfe', borderRadius: 20, padding: '1px 7px' }}>
                                                <svg style={{ width: 8, height: 8, animation: 'spin 1s linear infinite', display: 'inline' }} viewBox="0 0 24 24" fill="none">
                                                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" style={{ opacity: 0.25 }} />
                                                    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" style={{ opacity: 0.75 }} />
                                                </svg>
                                                RUNNING
                                            </span>
                                        </div>
                                        <p style={{ fontSize: 11, color: '#3b82f6', margin: '3px 0 0' }}>{AGENT_META[currentAgent]?.description}</p>
                                    </div>
                                </div>
                            )}
                            <div ref={feedBottomRef} />
                        </div>
                    </div>

                    {/* Phase message (only during processing) */}
                    {!isApproval && (
                        <p style={{ fontSize: 12, color: '#475569', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '10px 14px', margin: '0 0 4px', lineHeight: 1.5 }}>
                            {phaseMessage}
                        </p>
                    )}

                    {/* ── APPROVAL PANEL ──────────────────────────────────────────── */}
                    {isApproval && (
                        <>
                            <div style={{ borderRadius: 14, border: '1px solid #fde68a', background: '#fffbeb', padding: 20, marginBottom: 14 }}>
                                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#92400e', margin: '0 0 8px' }}>⚠️ Why is approval needed?</h3>
                                <p style={{ fontSize: 12, color: '#78350f', margin: '0 0 14px', lineHeight: 1.7 }}>
                                    The <strong>Reviewer Agent</strong> completed its quality audit and flagged the issues below. These are <em>not</em> pipeline errors — they are confidence or consistency flags that need a human to verify before the final report is locked.
                                </p>
                                {reviewWarnings.length > 0 ? (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 14 }}>
                                        {reviewWarnings.map((w, i) => {
                                            const isLow = w.toLowerCase().includes('low confidence');
                                            const isPol = w.includes('[Policy Inconsistency]');
                                            const isCod = w.includes('[Coding Inconsistency]');
                                            const clr = isLow ? '#dc2626' : isPol ? '#7c3aed' : isCod ? '#d97706' : '#475569';
                                            const bg = isLow ? '#fef2f2' : isPol ? '#f5f3ff' : isCod ? '#fffbeb' : '#f8fafc';
                                            const border = isLow ? '#fecaca' : isPol ? '#ddd6fe' : isCod ? '#fde68a' : '#e2e8f0';
                                            const tag = isLow ? '🔴 Low Confidence' : isPol ? '🟣 Policy Inconsistency' : isCod ? '🟠 Coding Inconsistency' : '⚪ Note';
                                            return (
                                                <div key={i} style={{ background: bg, border: `1px solid ${border}`, borderRadius: 8, padding: '9px 13px' }}>
                                                    <span style={{ fontSize: 10, fontWeight: 700, color: clr, display: 'block', marginBottom: 4 }}>{tag}</span>
                                                    <span style={{ fontSize: 12, color: '#374151', lineHeight: 1.6 }}>{w.replace('[Policy Inconsistency] ', '').replace('[Coding Inconsistency] ', '')}</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    <p style={{ fontSize: 12, color: '#6b7280', fontStyle: 'italic', marginBottom: 14 }}>No specific warnings returned — generic quality check flagged.</p>
                                )}

                                <div style={{ borderTop: '1px solid #fde68a', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 9 }}>
                                    <div style={{ display: 'flex', gap: 9, alignItems: 'flex-start', fontSize: 12, color: '#374151' }}>
                                        <span style={{ background: '#d1fae5', color: '#065f46', border: '1px solid #a7f3d0', borderRadius: 20, padding: '2px 9px', fontWeight: 700, fontSize: 10, flexShrink: 0, marginTop: 1 }}>APPROVE</span>
                                        <span>Accept the current codes and <strong>generate the final COB report now</strong>. Use this if the flagged issues are acceptable for this clinical case.</span>
                                    </div>
                                    <div style={{ display: 'flex', gap: 9, alignItems: 'flex-start', fontSize: 12, color: '#374151' }}>
                                        <span style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fca5a5', borderRadius: 20, padding: '2px 9px', fontWeight: 700, fontSize: 10, flexShrink: 0, marginTop: 1 }}>REJECT</span>
                                        <span>Send the flags above back to <strong>Gemini as a reflection prompt</strong> — the Medical Coding Agent re-runs and tries to fix the specific issues.</span>
                                    </div>
                                </div>
                            </div>

                            {activeJobId && (
                                <div style={{ display: 'flex', gap: 10 }}>
                                    <button
                                        onClick={async () => {
                                            try {
                                                setPhaseMessage('Approving claim and finalizing reports...');
                                                await ApiService.approveAnalysis(activeJobId);
                                                setAnalysisStatus('processing');
                                                intervalRef.current = setInterval(async () => {
                                                    const r = await ApiService.getAnalysisStatus(activeJobId);
                                                    setProgress(r.progress_percent);
                                                    setPhaseMessage(r.message);
                                                    if (r.status === 'completed') {
                                                        if (intervalRef.current) clearInterval(intervalRef.current);
                                                        setTimeout(() => navigate(`/results?job_id=${activeJobId}`), 500);
                                                    }
                                                }, 1000);
                                            } catch {
                                                setErrorMessage('Failed to approve. Please retry.');
                                                setAnalysisStatus('failed');
                                            }
                                        }}
                                        style={{ flex: 1, borderRadius: 10, background: '#059669', color: '#fff', border: 'none', padding: '12px 0', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                                        ✅ Approve Claim
                                    </button>
                                    <button
                                        onClick={async () => {
                                            try {
                                                setPhaseMessage('Sending rejection + reflection prompt to Gemini...');
                                                setAgentFeed([]);
                                                setCurrentAgent(null);
                                                await ApiService.rejectAnalysis(activeJobId);
                                                setAnalysisStatus('processing');
                                                setProgress(40);
                                                intervalRef.current = buildPollingLoop(activeJobId, new Set<string>());
                                            } catch {
                                                setErrorMessage('Failed to submit rejection. Please retry.');
                                                setAnalysisStatus('failed');
                                            }
                                        }}
                                        style={{ flex: 1, borderRadius: 10, background: '#dc2626', color: '#fff', border: 'none', padding: '12px 0', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                                        🔄 Reject &amp; Refine
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
                <style>{`
                    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
                    @keyframes pulse {
                        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
                        70% { transform: scale(1.02); box-shadow: 0 0 0 6px rgba(59, 130, 246, 0); }
                        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
                    }
                `}</style>
            </PageContainer>
        );
    }

    // ── DEFAULT WORKSPACE ────────────────────────────────────────────────────
    return (
        <PageContainer className="max-w-4xl">
            <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: 20, marginBottom: 32 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', margin: 0 }}>Document Intake Workspace</h1>
                <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                    Upload all 4 required medical documents to begin the Coordination of Benefits analysis.
                </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <h2 style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', margin: 0 }}>Required Documents</h2>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        {activeFiles.length > 0 && (
                            <button onClick={resetWorkspace} style={{ fontSize: 11, fontWeight: 700, color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>Clear All</button>
                        )}
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8' }}>{activeFiles.length} of {requirementSlots.length} Satisfied</span>
                    </div>
                </div>

                {/* Empty state */}
                {isNoneUploaded && (
                    <div style={{ borderRadius: 14, border: '1px solid #bfdbfe', background: '#eff6ff', padding: '14px 18px', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                        <span style={{ fontSize: 20, flexShrink: 0 }}>📂</span>
                        <div>
                            <p style={{ fontSize: 13, fontWeight: 700, color: '#1e40af', margin: '0 0 4px' }}>No documents uploaded yet</p>
                            <p style={{ fontSize: 12, color: '#3b82f6', margin: 0 }}>
                                Please upload all 4 required documents below. Analysis cannot start until all slots are satisfied — <strong>no sample files are loaded automatically</strong>.
                            </p>
                        </div>
                    </div>
                )}

                {/* Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 20 }}>
                    {requirementSlots.map(slot => (
                        <RequirementSlotCard key={slot.id} slot={slot} file={uploadedFiles[slot.id]} onUpload={handleUpload} onRemove={handleRemove} />
                    ))}
                </div>

                {/* Guidelines */}
                <div style={{ borderRadius: 12, border: '1px solid #f1f5f9', background: '#f8fafc', padding: 16 }}>
                    <h3 style={{ fontSize: 10, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 8px' }}>Intake Guidelines</h3>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: '#64748b', lineHeight: 1.9 }}>
                        <li>Drag and drop files onto each card, or click to choose a file.</li>
                        <li>Only one file can occupy each slot at a time.</li>
                        <li>Files are uploaded to the backend before analysis begins.</li>
                        <li><strong style={{ color: '#374151' }}>Currency:</strong> All invoices and estimates must list amounts in <strong style={{ color: '#374151' }}>Indian Rupees (INR / ₹)</strong>.</li>
                    </ul>
                </div>

                {/* All-uploaded banner + Start */}
                {isAllUploaded && (
                    <div style={{ borderRadius: 14, border: '1px solid #a7f3d0', background: '#f0fdf4', padding: 20 }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                            <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#d1fae5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, flexShrink: 0 }}>✓</div>
                            <div style={{ flex: 1 }}>
                                <h4 style={{ fontSize: 14, fontWeight: 700, color: '#065f46', margin: '0 0 4px' }}>All 4 Documents Uploaded</h4>
                                <p style={{ fontSize: 12, color: '#059669', margin: '0 0 16px' }}>The orchestrator is ready to begin Coordination of Benefits reasoning across 7 specialist AI agents.</p>
                                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 16 }}>
                                    <div>
                                        <label style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.07em', display: 'block', marginBottom: 6 }}>Run Mode (Select Demo for Mock Run)</label>
                                        <div style={{ display: 'flex', background: '#e2e8f0', borderRadius: 10, padding: 3, gap: 3, border: '1px solid #cbd5e1' }}>
                                            <button type="button" onClick={() => setMockMode(true)}
                                                style={{ padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 700, cursor: 'pointer', border: mockMode ? '1px solid #cbd5e1' : '1px solid transparent', background: mockMode ? '#fff' : 'transparent', color: mockMode ? '#1e293b' : '#64748b', boxShadow: mockMode ? '0 1px 3px rgba(0,0,0,0.08)' : 'none', transition: 'all 0.15s' }}>
                                                Demo (Mock Run)
                                            </button>
                                            <button type="button" onClick={() => setMockMode(false)}
                                                style={{ padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 700, cursor: 'pointer', border: !mockMode ? '1px solid #cbd5e1' : '1px solid transparent', background: !mockMode ? '#fff' : 'transparent', color: !mockMode ? '#1e293b' : '#64748b', boxShadow: !mockMode ? '0 1px 3px rgba(0,0,0,0.08)' : 'none', transition: 'all 0.15s' }}>
                                                Production (Gemini)
                                            </button>
                                        </div>
                                    </div>
                                    <div>
                                        <label style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.07em', display: 'block', marginBottom: 6 }}>Image OCR Engine</label>
                                        <div style={{ display: 'flex', background: '#e2e8f0', borderRadius: 10, padding: 3, gap: 3, border: '1px solid #cbd5e1', opacity: mockMode ? 0.5 : 1, pointerEvents: mockMode ? 'none' : 'auto' }}>
                                            {(['library', 'gemini'] as const).map(eng => (
                                                <button key={eng} type="button" onClick={() => setOcrEngine(eng)} disabled={mockMode}
                                                    style={{ padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 700, cursor: mockMode ? 'default' : 'pointer', border: ocrEngine === eng ? '1px solid #cbd5e1' : '1px solid transparent', background: ocrEngine === eng ? '#fff' : 'transparent', color: ocrEngine === eng ? '#1e293b' : '#64748b', boxShadow: ocrEngine === eng ? '0 1px 3px rgba(0,0,0,0.08)' : 'none', transition: 'all 0.15s' }}>
                                                    {eng === 'library' ? 'Local OCR (Default)' : 'Gemini Vision OCR'}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <button onClick={startAssessment} type="button"
                                        style={{ borderRadius: 10, background: '#2563eb', color: '#fff', border: 'none', padding: '12px 22px', fontSize: 13, fontWeight: 700, cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.3)', transition: 'background 0.15s', alignSelf: 'flex-end' }}
                                        onMouseEnter={e => (e.currentTarget.style.background = '#1d4ed8')}
                                        onMouseLeave={e => (e.currentTarget.style.background = '#2563eb')}>
                                        🚀 Start Assessment
                                    </button>
                                    <span style={{ fontSize: 11, color: '#94a3b8', alignSelf: 'flex-end', paddingBottom: 4 }}>Orchestrates 7 specialist agents</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </PageContainer>
    );
};
