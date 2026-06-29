import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { RequirementSlotCard } from '../../components/intake/RequirementSlotCard';
import type { RequirementSlot, RequirementSlotId, UploadedFile } from '../../types/intake';
import { ApiService } from '../../services/api';

export const IntakePage: React.FC = () => {
    const navigate = useNavigate();
    
    // Predefined requirement slots
    const requirementSlots: RequirementSlot[] = [
        {
            id: 'priya_pt_invoice',
            title: 'Priya PT Invoice',
            description: 'Physical therapy invoice containing detailed billing codes, sessions, and amounts.',
            allowedFormats: ['.pdf', '.png', '.jpg', '.jpeg'],
        },
        {
            id: 'aarav_mri_report',
            title: 'Aarav MRI Report',
            description: 'Magnetic resonance imaging radiology report highlighting medical findings.',
            allowedFormats: ['.pdf', '.png', '.jpg', '.jpeg'],
        },
        {
            id: 'surgeon_estimate',
            title: 'Surgeon Estimate',
            description: 'Fee estimate sheet detailing the surgery procedure codes, facility costs, and provider pricing.',
            allowedFormats: ['.pdf', '.png', '.jpg', '.jpeg'],
        },
        {
            id: 'user_query_transcript',
            title: 'User Query Transcript',
            description: 'A text transcript containing the user coordination query or benefit question.',
            allowedFormats: ['.txt', '.pdf'],
        },
    ];

    // State to hold the files satisfying each slot
    const [uploadedFiles, setUploadedFiles] = useState<Record<RequirementSlotId, UploadedFile | undefined>>({
        priya_pt_invoice: undefined,
        aarav_mri_report: undefined,
        surgeon_estimate: undefined,
        user_query_transcript: undefined,
    });

    // Analysis coordination states
    const [analysisStatus, setAnalysisStatus] = useState<'idle' | 'starting' | 'processing' | 'completed' | 'failed'>('idle');
    const [progress, setProgress] = useState(0);
    const [phaseMessage, setPhaseMessage] = useState('');
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [failedAgent, setFailedAgent] = useState<string | null>(null);
    const [ocrEngine, setOcrEngine] = useState<'library' | 'gemini'>('library');

    // Fetch existing files from backend storage on mount
    useEffect(() => {
        const fetchIntakeStatus = async () => {
            try {
                const syncedFiles = await ApiService.fetchIntakeStatus();
                setUploadedFiles(syncedFiles);
            } catch (err) {
                console.warn('Could not sync files from backend on mount. Using local storage state.', err);
            }
        };
        fetchIntakeStatus();
    }, []);

    const handleUpload = async (file: File, slotId: RequirementSlotId) => {
        // Set local state to uploading first
        setUploadedFiles((prev) => ({
            ...prev,
            [slotId]: {
                name: file.name,
                size: file.size,
                type: file.type,
                status: 'uploading',
                slotId,
            },
        }));

        try {
            const uploadedFile = await ApiService.uploadDocument(file, slotId);
            setUploadedFiles((prev) => ({
                ...prev,
                [slotId]: uploadedFile,
            }));
        } catch (err: any) {
            let errorMsg = 'Upload failed. Please check network connection.';
            
            if (axios.isAxiosError(err)) {
                if (err.response) {
                    // Extract validation error message from starlette/fastapi error schema
                    errorMsg = err.response.data?.detail || `Server returned error status ${err.response.status}`;
                } else if (err.request) {
                    errorMsg = 'No response received from the backend server.';
                }
            }
            
            console.warn(`Backend upload failed for ${slotId}: ${errorMsg}`, err);

            setUploadedFiles((prev) => ({
                ...prev,
                [slotId]: {
                    name: file.name,
                    size: file.size,
                    type: file.type,
                    status: 'error',
                    slotId,
                    errorMsg,
                },
            }));
        }
    };

    const handleRemove = async (slotId: RequirementSlotId) => {
        // Optimistically remove locally
        setUploadedFiles((prev) => ({
            ...prev,
            [slotId]: undefined,
        }));

        try {
            await ApiService.deleteDocument(slotId);
        } catch (err) {
            console.warn(`Backend deletion failed for slot ${slotId}.`, err);
        }
    };

    const startAssessment = async () => {
        setAnalysisStatus('starting');
        setProgress(10);
        setPhaseMessage('Contacting backend Benefit Orchestrator...');

        try {
            // 1. Post to start analysis
            const { job_id } = await ApiService.startAnalysis(ocrEngine);
            setAnalysisStatus('processing');

            // 2. Poll job status
            const interval = setInterval(async () => {
                try {
                    const { status: jobStatus, progress_percent, message, error_details } = await ApiService.getAnalysisStatus(job_id);

                    setProgress(progress_percent);
                    setPhaseMessage(message);

                    if (jobStatus === 'completed') {
                        clearInterval(interval);
                        setTimeout(() => {
                            navigate(`/results?job_id=${job_id}`);
                        }, 500);
                    } else if (jobStatus === 'failed') {
                        clearInterval(interval);
                        setAnalysisStatus('failed');
                        setErrorMessage(message || error_details || 'Pipeline failed. Check backend logs for details.');
                    }
                } catch (pollErr: any) {
                    clearInterval(interval);
                    console.error('Polling check failed:', pollErr);
                    setAnalysisStatus('failed');
                    setErrorMessage('Lost connection to backend while polling analysis status. Please retry.');
                }
            }, 1200);
        } catch (err: any) {
            console.error('Backend server not responding:', err);
            setAnalysisStatus('failed');
            const detail = err?.response?.data?.detail;
            setErrorMessage(typeof detail === 'string' ? detail : 'Backend server is not responding. Ensure the server is running on port 8000.');
        }
    };

    const resetWorkspace = async () => {
        // Clear all files on backend
        const slotsToClear = Object.keys(uploadedFiles) as RequirementSlotId[];
        for (const slotId of slotsToClear) {
            if (uploadedFiles[slotId]) {
                try {
                    await ApiService.deleteDocument(slotId);
                } catch (err) {
                    console.warn(`Failed to clean backend storage slot ${slotId} on reset.`, err);
                }
            }
        }

        setUploadedFiles({
            priya_pt_invoice: undefined,
            aarav_mri_report: undefined,
            surgeon_estimate: undefined,
            user_query_transcript: undefined,
        });
        setAnalysisStatus('idle');
        setProgress(0);
        setPhaseMessage('');
    };

    // Compute metrics
    const activeFiles = Object.values(uploadedFiles).filter((f) => f && f.status === 'ready') as UploadedFile[];
    const isWorkspaceEmpty = Object.values(uploadedFiles).filter(Boolean).length === 0;
    const isAllUploaded = requirementSlots.every((slot) => uploadedFiles[slot.id]?.status === 'ready');

    // Render failed state
    if (analysisStatus === 'failed') {
        return (
            <PageContainer className="max-w-xl py-16">
                <div className="rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-md">
                    <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-rose-50 text-rose-600">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-8 w-8">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                        </svg>
                    </div>

                    <h2 className="mt-6 text-xl font-bold text-slate-900">Pipeline Failed</h2>
                    <p className="mt-1.5 text-xs text-slate-400 font-semibold tracking-wide uppercase">Multi-Agent Orchestration Error</p>

                    {failedAgent && (
                        <div className="mt-4 inline-flex items-center rounded-full bg-rose-50 px-3 py-1 text-xs font-bold text-rose-700 ring-1 ring-inset ring-rose-600/10">
                            Failed at: {failedAgent}
                        </div>
                    )}

                    <p className="mt-4 text-sm font-medium text-rose-700 bg-rose-50 border border-rose-100 rounded-xl py-3.5 px-5">
                        {errorMessage || 'An unknown error occurred during pipeline execution.'}
                    </p>

                    <div className="mt-6 flex justify-center gap-3">
                        <button
                            onClick={() => {
                                setAnalysisStatus('idle');
                                setProgress(0);
                                setPhaseMessage('');
                                setErrorMessage(null);
                                setFailedAgent(null);
                            }}
                            type="button"
                            className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors cursor-pointer"
                        >
                            Retry Assessment
                        </button>
                    </div>
                </div>
            </PageContainer>
        );
    }

    // Render Loading / Progress state
    if (analysisStatus === 'starting' || analysisStatus === 'processing') {
        return (
            <PageContainer className="max-w-xl py-16">
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-md">
                    <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-50 text-blue-600">
                        <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    </div>

                    <h2 className="mt-6 text-xl font-bold text-slate-900">Analyzing Benefits</h2>
                    <p className="mt-1.5 text-xs text-slate-400 font-semibold tracking-wide uppercase">Orchestrating AI Agents via Google ADK</p>

                    {/* Progress Bar */}
                    <div className="mt-8">
                        <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                            <div
                                className="h-full bg-blue-600 transition-all duration-500 rounded-full"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                        <div className="mt-2.5 flex justify-between text-[10px] font-bold text-slate-400 uppercase">
                            <span>Progress</span>
                            <span>{progress}%</span>
                        </div>
                    </div>

                    {/* Current Phase Message */}
                    <p className="mt-6 text-sm font-medium text-slate-650 bg-slate-50 border border-slate-100 rounded-xl py-3.5 px-5">
                        {phaseMessage}
                    </p>
                </div>
            </PageContainer>
        );
    }

    // Render default Workspace
    return (
        <PageContainer className="max-w-4xl">
            {/* Page Header */}
            <div className="border-b border-slate-200 pb-5 mb-8">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">Document Intake Workspace</h1>
                <p className="text-sm text-slate-550 mt-1">
                    Prepare and organize the required medical and estimate files before launching the Coordination of Benefits (COB) analysis.
                </p>
            </div>

            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                        Required Documents List
                    </h2>
                    <div className="flex items-center gap-4">
                        {!isWorkspaceEmpty && (
                            <button
                                onClick={resetWorkspace}
                                type="button"
                                className="text-xs font-bold text-rose-600 hover:text-rose-700 transition-colors cursor-pointer"
                            >
                                Clear All
                            </button>
                        )}
                        <span className="text-xs font-semibold text-slate-400">
                            {activeFiles.length} of {requirementSlots.length} Satisfied
                        </span>
                    </div>
                </div>

                {/* Requirements Grid */}
                <div className="grid gap-6 sm:grid-cols-2">
                    {requirementSlots.map((slot) => (
                        <RequirementSlotCard
                            key={slot.id}
                            slot={slot}
                            file={uploadedFiles[slot.id]}
                            onUpload={handleUpload}
                            onRemove={handleRemove}
                        />
                    ))}
                </div>

                {/* Intake guidelines panel */}
                <div className="rounded-xl border border-slate-150 bg-slate-50/50 p-4 text-xs text-slate-500">
                    <h3 className="font-semibold text-slate-700 mb-1.5 uppercase tracking-wider text-[10px]">
                        Intake Guidelines
                    </h3>
                    <ul className="space-y-1 list-disc pl-4">
                        <li>Drag and drop files directly onto each card, or click a card to choose files.</li>
                        <li>Only one file can occupy each requirement card at a time.</li>
                        <li>Files are securely uploaded and stored in the backend service for analysis.</li>
                        <li><strong className="text-slate-700">Currency Requirement:</strong> Please ensure that all uploaded invoices, estimate sheets, and documents list financial amounts in <strong className="text-slate-700">Indian Rupees (INR / ₹)</strong>.</li>
                    </ul>
                </div>

                {/* Ready to Process Status Banner */}
                {isAllUploaded && (
                    <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-5 mt-6 transition-all">
                        <div className="flex items-start gap-3">
                            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    strokeWidth={2.5}
                                    stroke="currentColor"
                                    className="h-3.5 w-3.5"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                                </svg>
                            </div>
                            <div className="flex-1 min-w-0">
                                <h4 className="text-sm font-bold text-slate-900">Intake Workspace Satisfied</h4>
                                <p className="text-xs text-slate-550 mt-1">
                                    All 4 required files have been verified. The orchestrator is prepared for Coordination of Benefits reasoning.
                                </p>

                                <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-center">
                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Image OCR Engine Choice</label>
                                        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 w-fit">
                                            <button
                                                type="button"
                                                onClick={() => setOcrEngine('library')}
                                                className={`px-3 py-1.5 rounded-md text-[11px] font-bold transition-all duration-200 cursor-pointer ${
                                                    ocrEngine === 'library'
                                                        ? 'bg-white text-slate-800 shadow-sm border border-slate-200/50'
                                                        : 'text-slate-500 hover:text-slate-800 border border-transparent'
                                                }`}
                                            >
                                                Local OCR Library (Default)
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setOcrEngine('gemini')}
                                                className={`px-3 py-1.5 rounded-md text-[11px] font-bold transition-all duration-200 cursor-pointer ${
                                                    ocrEngine === 'gemini'
                                                        ? 'bg-white text-slate-800 shadow-sm border border-slate-200/50'
                                                        : 'text-slate-500 hover:text-slate-800 border border-transparent'
                                                }`}
                                            >
                                                Gemini Vision OCR
                                            </button>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3 self-end sm:mb-[2px]">
                                        <button
                                            onClick={startAssessment}
                                            type="button"
                                            className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors cursor-pointer"
                                        >
                                            Start Assessment
                                        </button>
                                        <span className="text-[10px] font-medium text-slate-400">
                                            (Orchestrates specialist agents)
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </PageContainer>
    );
};
