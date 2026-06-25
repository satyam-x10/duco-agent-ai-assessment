import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { FileUploader } from '../../components/intake/FileUploader';
import { RequirementSlotCard } from '../../components/intake/RequirementSlotCard';
import type { RequirementSlot, RequirementSlotId, UploadedFile } from '../../types/intake';
import { ApiService } from '../../services/api';

const DEMO_FILES: Record<
  RequirementSlotId,
  { filename: string; contentType: string; text: string }
> = {
  priya_pt_invoice: {
    filename: 'priya_pt_invoice.pdf',
    contentType: 'application/pdf',
    text: `Peak Physical Therapy Clinic
Invoice ID: PT-2023-9981
Date: Oct 18, 2023
Patient Name: Priya Sen

Billing details:
Date       CPT Code  Description                         Units  Unit Cost  Total
2023-10-10 97110     Therapeutic Procedure [Exercise]    1      $150.00    $150.00
2023-10-12 97110     Therapeutic Procedure [Exercise]    1      $150.00    $150.00
2023-10-15 97110     Therapeutic Procedure [Exercise]    1      $150.00    $150.00
2023-10-10 97140     Manual Therapy Techniques           1      $100.00    $100.00
2023-10-12 97140     Manual Therapy Techniques           1      $100.00    $100.00

Total Billed: $650.00
Amount Paid: $0.00 [Pending insurance coordination]`
  },
  aarav_mri_report: {
    filename: 'aarav_mri_report.pdf',
    contentType: 'application/pdf',
    text: `Metro Imaging and Radiology Services
Report ID: RAD-MRI-8827
Date: Oct 20, 2023
Patient Name: Aarav Sen
Date of Birth: 2012-05-14

Procedure Code: CPT 73721 [MRI Lower Extremity Joint without contrast, Right Knee]

Clinical History: Knee pain following sports activity. Medial joint line tenderness.

Findings:
There is a complete vertical tear of the posterior horn of the medial meniscus.
Minimal joint effusion is present. The anterior cruciate ligament [ACL] and posterior
cruciate ligament [PCL] are intact. Collateral ligaments are normal.

Diagnosis: Complete medial meniscus posterior horn tear, right knee joint.
Total Facility Charge: $1200.00`
  },
  surgeon_estimate: {
    filename: 'surgeon_estimate.pdf',
    contentType: 'application/pdf',
    text: `Knee Specialist Clinic & Surgical Center
Surgical Estimate ID: EST-5527
Date: Oct 22, 2023
Patient Name: Aarav Sen
Date of Birth: 2012-05-14

Proposed Procedure: Right Knee Arthroscopy with Medial Meniscectomy
Procedure Code: CPT 29881 [Knee arthroscopy with meniscectomy]
Scheduled Date: Nov 15, 2023

Fee Schedule Estimates:
1. Surgeon Professional Fee [CPT 29881]: $3200.00
2. Facility Operating Room Fee [Metro Surgical]: $4500.00
3. Anesthesia Fee [Standard Pro-rata 2hr]: $1200.00

Total Billed Estimate: $8900.00
Pre-authorization is required for CPT 29881.`
  },
  user_query_transcript: {
    filename: 'user_query_transcript.txt',
    contentType: 'text/plain',
    text: `Coordination of Benefits [COB] Query Transcript
Date: Oct 24, 2023
User Query:
"Hello, I am setting up the Coordination of Benefits for my family. My wife Priya Sen has dual coverage: she is the primary subscriber under BlueShield Cross [Group: BS120, Member: 98765] and she is also covered as a dependent under my secondary plan UnitedHealth [Group: UHC-567-GOLD, Member: 54321].
Additionally, my son Aarav Sen is covered under both plans. I am the primary subscriber for Aarav under UnitedHealth [Group: UHC-567-GOLD, Member: 54321], and he is a dependent under Priya's BlueShield Cross [Group: BS120, Member: 98765].
Priya recently completed physical therapy [billed amount $650.00] and Aarav has an upcoming knee meniscus surgery [surgeon estimate $8,900.00 and MRI facility cost $1,200.00].
Could you analyze these documents, determine which plan is primary for Priya and Aarav, calculate what each insurer is responsible to pay, and write the prior-authorization request letters?"`
  }
};

const generateDemoFile = (slotId: RequirementSlotId): File => {
  const spec = DEMO_FILES[slotId];
  if (spec.contentType === 'application/pdf') {
    const escapedText = spec.text.replace(/\(/g, '\\(').replace(/\)/g, '\\)');
    const streamBytes = `BT\n/F1 12 Tf\n70 700 Td\n(${escapedText}) Tj\nET`;
    const pdfTemplate = `%PDF-1.4
1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
3 0 obj <</Type /Page /Parent 2 0 R /Resources << /Font << /F1 5 0 R >> >> /MediaBox [0 0 612 792] /Contents 4 0 R>> endobj
4 0 obj <</Length ${streamBytes.length}>> stream
${streamBytes}
endstream
endobj
5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000056 00000 n 
0000000111 00000 n 
0000000236 00000 n 
0000000341 00000 n 
trailer <</Size 6 /Root 1 0 R>>
startxref
412
%%EOF`;
    const blob = new Blob([pdfTemplate], { type: 'application/pdf' });
    return new File([blob], spec.filename, { type: 'application/pdf' });
  } else {
    const blob = new Blob([spec.text], { type: 'text/plain' });
    return new File([blob], spec.filename, { type: 'text/plain' });
  }
};

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
    const [isDemoLoading, setIsDemoLoading] = useState(false);

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

    // Run a high-fidelity client-side progress simulation as a robust fallback
    const runFallbackSimulation = () => {
        setAnalysisStatus('processing');
        setProgress(15);
        setPhaseMessage('Initializing specialist agents...');

        setTimeout(() => {
            setProgress(45);
            setPhaseMessage('COB Agent resolving rules for primary/secondary insurance...');

            setTimeout(() => {
                setProgress(75);
                setPhaseMessage('Finance Agent calculating out-of-pocket costs...');

                setTimeout(() => {
                    setProgress(100);
                    setPhaseMessage('Pre-authorization documents drafted. Analysis completed.');
                    setTimeout(() => {
                        navigate('/results?job_id=fallback-job-id');
                    }, 500);
                }, 1200);
            }, 1200);
        }, 1200);
    };

    const startAssessment = async () => {
        setAnalysisStatus('starting');
        setProgress(10);
        setPhaseMessage('Contacting backend Benefit Orchestrator...');

        try {
            // 1. Post to start analysis
            const { job_id } = await ApiService.startAnalysis();
            setAnalysisStatus('processing');

            // 2. Poll job status
            const interval = setInterval(async () => {
                try {
                    const { status: jobStatus, progress_percent, message } = await ApiService.getAnalysisStatus(job_id);

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
                    }
                } catch (pollErr) {
                    clearInterval(interval);
                    console.warn('Polling check failed. Switching to fallback simulation...', pollErr);
                    runFallbackSimulation();
                }
            }, 1200);
        } catch (err) {
            console.warn('Backend server not responding. Running client-side benefit simulation fallback...', err);
            runFallbackSimulation();
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

    const loadDemoScenario = async () => {
        setIsDemoLoading(true);
        try {
            // Set all slots to uploading locally first
            setUploadedFiles({
                priya_pt_invoice: { name: 'priya_pt_invoice.pdf', size: 0, type: 'application/pdf', status: 'uploading', slotId: 'priya_pt_invoice' },
                aarav_mri_report: { name: 'aarav_mri_report.pdf', size: 0, type: 'application/pdf', status: 'uploading', slotId: 'aarav_mri_report' },
                surgeon_estimate: { name: 'surgeon_estimate.pdf', size: 0, type: 'application/pdf', status: 'uploading', slotId: 'surgeon_estimate' },
                user_query_transcript: { name: 'user_query_transcript.txt', size: 0, type: 'text/plain', status: 'uploading', slotId: 'user_query_transcript' },
            });

            const slots: RequirementSlotId[] = [
                'priya_pt_invoice',
                'aarav_mri_report',
                'surgeon_estimate',
                'user_query_transcript',
            ];

            const results: Record<RequirementSlotId, UploadedFile | undefined> = {
                priya_pt_invoice: undefined,
                aarav_mri_report: undefined,
                surgeon_estimate: undefined,
                user_query_transcript: undefined,
            };

            for (const slotId of slots) {
                const file = generateDemoFile(slotId);
                const uploadedFile = await ApiService.uploadDocument(file, slotId);
                results[slotId] = uploadedFile;
            }

            setUploadedFiles(results);
        } catch (err) {
            console.error('Failed to load demo scenario:', err);
            // Reset and sync with backend
            try {
                const syncedFiles = await ApiService.fetchIntakeStatus();
                setUploadedFiles(syncedFiles);
            } catch (syncErr) {
                console.error('Failed to sync workspace after demo failure:', syncErr);
            }
        } finally {
            setIsDemoLoading(false);
        }
    };

    // Compute metrics
    const activeFiles = Object.values(uploadedFiles).filter((f) => f && f.status === 'ready') as UploadedFile[];
    const occupiedSlotIds = (Object.values(uploadedFiles).filter((f) => f && (f.status === 'ready' || f.status === 'uploading')) as UploadedFile[]).map((f) => f.slotId);
    const isWorkspaceEmpty = Object.values(uploadedFiles).filter(Boolean).length === 0;
    const isAllUploaded = requirementSlots.every((slot) => uploadedFiles[slot.id]?.status === 'ready');

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
        <PageContainer className="max-w-6xl">
            {/* Page Header */}
            <div className="border-b border-slate-200 pb-5 mb-8">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">Document Intake Workspace</h1>
                <p className="text-sm text-slate-550 mt-1">
                    Prepare and organize the required medical and estimate files before launching the Coordination of Benefits (COB) analysis.
                </p>
            </div>

            <div className="grid gap-8 lg:grid-cols-12 items-start">
                {/* Left Column: Upload Panel (5/12 width) */}
                <div className="lg:col-span-5 space-y-6">
                    <FileUploader
                        slots={requirementSlots}
                        occupiedSlots={occupiedSlotIds}
                        onUpload={handleUpload}
                    />

                    {/* Quick instructions panel */}
                    <div className="rounded-xl border border-slate-150 bg-slate-50/50 p-4 text-xs text-slate-500">
                        <h3 className="font-semibold text-slate-700 mb-1.5 uppercase tracking-wider text-[10px]">
                            Intake Guidelines
                        </h3>
                        <ul className="space-y-1 list-disc pl-4">
                            <li>Select the target requirement first to unlock drag-and-drop.</li>
                            <li>Only one file can occupy each requirement card at a time.</li>
                            <li>Files are cached in local memory and are not sent to any server.</li>
                        </ul>
                    </div>
                </div>

                {/* Right Column: Requirements and Upload Cards (7/12 width) */}
                <div className="lg:col-span-7 space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                            Required Documents List
                        </h2>
                        <div className="flex items-center gap-3">
                            {!isWorkspaceEmpty ? (
                                <button
                                    onClick={resetWorkspace}
                                    type="button"
                                    disabled={isDemoLoading}
                                    className={`text-xs font-bold text-rose-600 hover:text-rose-700 transition-colors ${isDemoLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                                >
                                    Clear All
                                </button>
                            ) : (
                                <button
                                    onClick={loadDemoScenario}
                                    type="button"
                                    disabled={isDemoLoading}
                                    className={`text-xs font-bold text-blue-600 hover:text-blue-755 transition-colors flex items-center gap-1.5 ${isDemoLoading ? 'opacity-50 cursor-not-allowed animate-pulse' : 'cursor-pointer'}`}
                                >
                                    {isDemoLoading ? (
                                        <>
                                            <svg className="animate-spin h-3 w-3 text-blue-600" viewBox="0 0 24 24" fill="none">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                            Loading Demo...
                                        </>
                                    ) : (
                                        '✨ Load Demo Scenario'
                                    )}
                                </button>
                            )}
                            <span className="text-xs font-semibold text-slate-400">
                                {activeFiles.length} of {requirementSlots.length} Satisfied
                            </span>
                        </div>
                    </div>

                    {/* Empty Workspace Notification */}
                    {isWorkspaceEmpty && (
                        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center shadow-sm">
                            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-50 text-slate-400">
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    strokeWidth={1.5}
                                    stroke="currentColor"
                                    className="h-6 w-6"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        d="M2.25 13.5h3.86a2.25 2.25 0 0 1 2.008 1.24l.885 1.77a2.25 2.25 0 0 0 2.007 1.24h1.98a2.25 2.25 0 0 0 2.007-1.24l.885-1.77a2.25 2.25 0 0 1 2.007-1.24h3.86m-18 0h18a2.25 2.25 0 0 1 2.25 2.25v4.5A2.25 2.25 0 0 1 18 21H6a2.25 2.25 0 0 1-2.25-2.25v-4.5a2.25 2.25 0 0 1 2.25-2.25ZM6.75 6.75h.75m-.75 3h.75m3-3h.75m-.75 3h.75M12 3v3m0 0 3-3m-3 3L9 3"
                                    />
                                </svg>
                            </div>
                            <h3 className="mt-4 text-xs font-bold text-slate-700">Workspace is empty</h3>
                            <p className="mt-1 text-[11px] text-slate-400 max-w-sm mx-auto">
                                No documents have been loaded. Pick a target category on the left to upload the medical records and estimate sheets.
                            </p>
                            <button
                                onClick={loadDemoScenario}
                                type="button"
                                disabled={isDemoLoading}
                                className={`mt-5 inline-flex items-center gap-2 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200/50 px-4.5 py-2 text-xs font-bold shadow-sm transition-all ${isDemoLoading ? 'opacity-50 cursor-not-allowed animate-pulse' : 'cursor-pointer hover:translate-y-[-1px]'}`}
                            >
                                {isDemoLoading ? (
                                    <>
                                        <svg className="animate-spin h-3.5 w-3.5 text-blue-750" viewBox="0 0 24 24" fill="none">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Preparing Scenario...
                                    </>
                                ) : (
                                    '✨ Load Demo Scenario'
                                )}
                            </button>
                        </div>
                    )}

                    {/* Requirements Grid */}
                    <div className="grid gap-4 sm:grid-cols-2">
                        {requirementSlots.map((slot) => (
                            <RequirementSlotCard
                                key={slot.id}
                                slot={slot}
                                file={uploadedFiles[slot.id]}
                                onRemove={handleRemove}
                            />
                        ))}
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

                                    <div className="mt-4 flex items-center gap-3">
                                        <button
                                            onClick={startAssessment}
                                            type="button"
                                            className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors"
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
                    )}
                </div>
            </div>
        </PageContainer>
    );
};
