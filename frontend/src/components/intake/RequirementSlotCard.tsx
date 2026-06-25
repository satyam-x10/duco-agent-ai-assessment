import React from 'react';
import type { RequirementSlot, UploadedFile } from '../../types/intake';

interface RequirementSlotCardProps {
  slot: RequirementSlot;
  file: UploadedFile | undefined;
  onRemove: (slotId: RequirementSlot['id']) => void;
}

export const RequirementSlotCard: React.FC<RequirementSlotCardProps> = ({
  slot,
  file,
  onRemove,
}) => {
  // Format file size helper
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className={`rounded-xl border p-5 transition-all bg-white shadow-sm ${
      file ? 'border-blue-150' : 'border-slate-200'
    }`}>
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
              <p className="mt-1 text-xs font-semibold text-red-650 leading-normal bg-red-50/50 border border-red-100 rounded-lg p-2">
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
              onClick={() => onRemove(slot.id)}
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-400 hover:text-red-500 hover:border-red-100 hover:bg-red-50/50 transition-colors"
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
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-800">{slot.title}</h3>
            <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/10">
              Missing
            </span>
          </div>
          <p className="mt-1.5 text-xs text-slate-400 leading-normal">{slot.description}</p>
          <div className="mt-4 text-[10px] text-slate-350 uppercase tracking-wider font-semibold">
            Accepts: {slot.allowedFormats.join(', ')}
          </div>
        </div>
      )}
    </div>
  );
};
