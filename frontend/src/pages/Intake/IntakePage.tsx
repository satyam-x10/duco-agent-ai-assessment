import React, { useState } from 'react';
import { PageContainer } from '../../components/layout/PageContainer';
import { FileUploader } from '../../components/intake/FileUploader';
import { RequirementSlotCard } from '../../components/intake/RequirementSlotCard';
import type { RequirementSlot, RequirementSlotId, UploadedFile } from '../../types/intake';

export const IntakePage: React.FC = () => {
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

  const handleUpload = (file: File, slotId: RequirementSlotId) => {
    setUploadedFiles((prev) => ({
      ...prev,
      [slotId]: {
        name: file.name,
        size: file.size,
        type: file.type,
        status: 'ready',
        slotId,
      },
    }));
  };

  const handleRemove = (slotId: RequirementSlotId) => {
    setUploadedFiles((prev) => ({
      ...prev,
      [slotId]: undefined,
    }));
  };

  // Compute metrics
  const activeFiles = Object.values(uploadedFiles).filter(Boolean) as UploadedFile[];
  const occupiedSlotIds = activeFiles.map((f) => f.slotId);
  const isWorkspaceEmpty = activeFiles.length === 0;
  const isAllUploaded = activeFiles.length === requirementSlots.length;

  return (
    <PageContainer className="max-w-6xl">
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-5 mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Document Intake Workspace</h1>
        <p className="text-sm text-slate-500 mt-1">
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
            <span className="text-xs font-semibold text-slate-400">
              {activeFiles.length} of {requirementSlots.length} Satisfied
            </span>
          </div>

          {/* Empty Workspace Notification */}
          {isWorkspaceEmpty && (
            <div className="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center shadow-sm">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-50 text-slate-400">
                {/* Document Tray Icon */}
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
                  <p className="text-xs text-slate-500 mt-1">
                    All 4 required files have been verified. The orchestrator is prepared for Coordination of Benefits reasoning.
                  </p>

                  <div className="mt-4 flex items-center gap-3">
                    <button
                      type="button"
                      disabled
                      className="rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm opacity-50 cursor-not-allowed"
                    >
                      Start Assessment
                    </button>
                    <span className="text-[10px] font-medium text-slate-400">
                      (ADK Orchestrator integration active in next milestone)
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
