import React, { useState, useRef, useEffect } from 'react';
import type { RequirementSlot, RequirementSlotId, UploadedFile } from '../../types/intake';

interface RequirementSlotCardProps {
  slot: RequirementSlot;
  file: UploadedFile | undefined;
  onRemove: (slotId: RequirementSlotId) => void;
  onUpload: (file: File, slotId: RequirementSlotId) => void;
}

const slotStyles: Record<
  RequirementSlotId,
  {
    borderActive: string;
    hoverBg: string;
    iconColor: string;
    badgeColor: string;
  }
> = {
  priya_pt_invoice: {
    borderActive: 'border-blue-500 bg-blue-50/15',
    hoverBg: 'hover:border-blue-300 hover:bg-blue-50/5',
    iconColor: 'text-blue-500 bg-blue-50',
    badgeColor: 'bg-blue-50 text-blue-700 ring-blue-600/10',
  },
  aarav_mri_report: {
    borderActive: 'border-indigo-500 bg-indigo-50/15',
    hoverBg: 'hover:border-indigo-300 hover:bg-indigo-50/5',
    iconColor: 'text-indigo-500 bg-indigo-50',
    badgeColor: 'bg-indigo-50 text-indigo-700 ring-indigo-600/10',
  },
  surgeon_estimate: {
    borderActive: 'border-emerald-500 bg-emerald-50/15',
    hoverBg: 'hover:border-emerald-300 hover:bg-emerald-50/5',
    iconColor: 'text-emerald-500 bg-emerald-50',
    badgeColor: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10',
  },
  user_query_transcript: {
    borderActive: 'border-amber-500 bg-amber-50/15',
    hoverBg: 'hover:border-amber-300 hover:bg-amber-50/5',
    iconColor: 'text-amber-500 bg-amber-50',
    badgeColor: 'bg-amber-50 text-amber-700 ring-amber-600/10',
  },
};

const renderSlotIcon = (id: RequirementSlotId) => {
  switch (id) {
    case 'priya_pt_invoice':
      return (
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
      );
    case 'aarav_mri_report':
      return (
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.03 0 1.9.732 2.112 1.704m-5.802 0a48.317 48.317 0 0 1-5.714.298C4.305 4.3 3.5 5.176 3.5 6.25v12.25a3.25 3.25 0 0 0 3.25 3.25h1.25m8.5-8.5v3.5a1.5 1.5 0 0 1-1.5 1.5H9a1.5 1.5 0 0 1-1.5-1.5v-3.5A1.5 1.5 0 0 1 9 10.5h3.75a1.5 1.5 0 0 1 1.5 1.5Z" />
        </svg>
      );
    case 'surgeon_estimate':
      return (
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75m-.75-3h1.5m18 15.75a9 9 0 0 1-9-9V4.5m0 12a9 9 0 0 1-9 9M9.75 3h4.5M9.75 6h4.5M9.75 9h4.5M9.75 12h4.5" />
        </svg>
      );
    case 'user_query_transcript':
      return (
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
        </svg>
      );
    default:
      return (
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
        </svg>
      );
  }
};

export const RequirementSlotCard: React.FC<RequirementSlotCardProps> = ({
  slot,
  file,
  onRemove,
  onUpload,
}) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setLocalError(null);
  }, [file]);

  const handleFile = (fileToProcess: File) => {
    setLocalError(null);
    const fileExtension = '.' + fileToProcess.name.split('.').pop()?.toLowerCase();
    const isExtensionValid = slot.allowedFormats.some(
      (ext) => ext.toLowerCase() === fileExtension
    );

    if (!isExtensionValid) {
      setLocalError(`Invalid file type. Supported formats: ${slot.allowedFormats.join(', ')}`);
      return;
    }

    // 10MB limit
    if (fileToProcess.size > 10 * 1024 * 1024) {
      setLocalError('File size exceeds the 10MB limit.');
      return;
    }

    onUpload(fileToProcess, slot.id);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const triggerBrowse = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Format file size helper
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const styles = slotStyles[slot.id];

  return (
    <div
      onDragEnter={!file ? handleDrag : undefined}
      onDragOver={!file ? handleDrag : undefined}
      onDragLeave={!file ? handleDrag : undefined}
      onDrop={!file ? handleDrop : undefined}
      onClick={!file ? triggerBrowse : undefined}
      className={`rounded-xl border p-5 transition-all bg-white shadow-sm duration-300 ${
        file
          ? 'border-blue-150'
          : isDragActive
            ? `${styles.borderActive} border-dashed`
            : `border-slate-200 border-dashed ${styles.hoverBg} cursor-pointer`
      }`}
    >
      {!file && (
        <input
          ref={fileInputRef}
          type="file"
          accept={slot.allowedFormats.join(',')}
          onChange={handleFileChange}
          className="hidden"
        />
      )}

      {file ? (
        // File Uploaded / Filled / Loading State Card
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">
              {slot.title}
            </span>
            <h3 className="mt-1 text-sm font-semibold text-slate-900 truncate" title={file.name}>
              {file.name}
            </h3>
            
            {file.status === 'error' && (
              <p className="mt-1 text-xs font-semibold text-red-650 leading-normal bg-red-50/55 border border-red-100 rounded-lg p-2">
                {file.errorMsg || 'Upload failed.'}
              </p>
            )}

            <div className="mt-2.5 flex items-center gap-3 text-xs text-slate-400">
              <span>{formatFileSize(file.size)}</span>
              <span>&bull;</span>
              
              {file.status === 'ready' && (
                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-650/10">
                  Ready
                </span>
              )}

              {file.status === 'uploading' && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-650/10">
                  <svg className="animate-spin h-3 w-3 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Uploading...
                </span>
              )}

              {file.status === 'error' && (
                <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-inset ring-red-650/10 animate-pulse">
                  Failed
                </span>
              )}
            </div>
          </div>

          {file.status !== 'uploading' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRemove(slot.id);
              }}
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-400 hover:text-red-500 hover:border-red-100 hover:bg-red-50/50 transition-colors cursor-pointer"
              title="Remove document"
            >
              {/* Trash icon SVG */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="h-4.5 w-4.5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                />
              </svg>
            </button>
          )}
        </div>
      ) : (
        // Missing Document / Empty State Card
        <div>
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${styles.iconColor}`}>
                {renderSlotIcon(slot.id)}
              </div>
              <h3 className="text-sm font-semibold text-slate-800">{slot.title}</h3>
            </div>
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${styles.badgeColor}`}>
              Missing
            </span>
          </div>
          
          <p className="mt-3 text-xs text-slate-400 leading-normal">{slot.description}</p>
          
          <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-100 pt-3 text-[10px] font-semibold">
            <span className="text-slate-400">
              Drag & drop file here or <span className="text-blue-600 hover:text-blue-700 underline">browse</span>
            </span>
            <span className="text-slate-350 uppercase tracking-wider">
              {slot.allowedFormats.join(', ')}
            </span>
          </div>

          {localError && (
            <div className="mt-3 rounded-lg bg-red-50 p-2.5 border border-red-100 flex items-start gap-2 text-xs text-red-750 leading-normal">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-4 w-4 text-red-500 mt-0.5 shrink-0">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
              </svg>
              <span>{localError}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
