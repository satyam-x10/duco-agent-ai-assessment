import React, { useRef, useState } from 'react';
import type { RequirementSlot, RequirementSlotId } from '../../types/intake';

interface FileUploaderProps {
  slots: RequirementSlot[];
  occupiedSlots: RequirementSlotId[];
  onUpload: (file: File, slotId: RequirementSlotId) => void;
}

export const FileUploader: React.FC<FileUploaderProps> = ({
  slots,
  occupiedSlots,
  onUpload,
}) => {
  const [selectedSlotId, setSelectedSlotId] = useState<RequirementSlotId | ''>('');
  const [isDragActive, setIsDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Filter allowed formats based on selected slot, or show general formats
  const currentSlot = slots.find((s) => s.id === selectedSlotId);
  const generalFormats = ['.pdf', '.png', '.jpg', '.jpeg', '.txt'];
  const allowedExtensions = currentSlot
    ? currentSlot.allowedFormats.map((f) => f.toLowerCase())
    : generalFormats;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const validateAndProcessFile = (file: File, targetSlotId: RequirementSlotId) => {
    setError(null);

    // Validate if slot is selected
    if (!targetSlotId) {
      setError('Please select which document requirement this file satisfies first.');
      return;
    }

    // Validate duplicate slot upload
    if (occupiedSlots.includes(targetSlotId)) {
      const slotName = slots.find((s) => s.id === targetSlotId)?.title || 'requirement';
      setError(`"${slotName}" has already been uploaded. Remove the current file to replace it.`);
      return;
    }

    // Validate extension
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    const slotRules = slots.find((s) => s.id === targetSlotId)?.allowedFormats || generalFormats;
    const isExtensionValid = slotRules.some((ext) => ext.toLowerCase() === fileExtension);

    if (!isExtensionValid) {
      setError(
        `Invalid file type. Supported formats for this slot are: ${slotRules.join(', ')}`
      );
      return;
    }

    // File limit check (e.g., 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('File size exceeds the 10MB limit.');
      return;
    }

    // Success - pass up to parent state
    onUpload(file, targetSlotId);
    setSelectedSlotId('');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    setError(null);

    if (!selectedSlotId) {
      setError('Please select a document requirement slot from the dropdown before uploading.');
      return;
    }

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndProcessFile(e.dataTransfer.files[0], selectedSlotId);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (!selectedSlotId) {
      setError('Please select a document requirement slot from the dropdown before uploading.');
      return;
    }

    if (e.target.files && e.target.files[0]) {
      validateAndProcessFile(e.target.files[0], selectedSlotId);
    }
  };

  const triggerBrowse = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4">
        Document Upload Zone
      </h2>

      {/* Target Slot Selector */}
      <div className="mb-4">
        <label htmlFor="slot-select" className="block text-xs font-semibold text-slate-500 uppercase mb-2">
          1. Select Requirement Target
        </label>
        <select
          id="slot-select"
          value={selectedSlotId}
          onChange={(e) => {
            setSelectedSlotId(e.target.value as RequirementSlotId);
            setError(null);
          }}
          className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none"
        >
          <option value="">-- Choose target slot --</option>
          {slots.map((s) => {
            const isFilled = occupiedSlots.includes(s.id);
            return (
              <option key={s.id} value={s.id} disabled={isFilled}>
                {s.title} {isFilled ? '(Occupied)' : ''}
              </option>
            );
          })}
        </select>
      </div>

      {/* Drag & Drop Zone */}
      <div className="mb-4">
        <span className="block text-xs font-semibold text-slate-500 uppercase mb-2">
          2. Drop or Browse File
        </span>
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-all ${
            isDragActive
              ? 'border-blue-500 bg-blue-50/10'
              : 'border-slate-250 bg-slate-50 hover:bg-slate-100/50'
          } ${!selectedSlotId ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
          onClick={() => selectedSlotId && triggerBrowse()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={allowedExtensions.join(',')}
            onChange={handleFileChange}
            disabled={!selectedSlotId}
            className="hidden"
          />

          {/* Upload Icon SVG */}
          <div className={`flex h-12 w-12 items-center justify-center rounded-full ${
            selectedSlotId ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-400'
          }`}>
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
                d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z"
              />
            </svg>
          </div>

          <p className="mt-4 text-xs font-semibold text-slate-700">
            {selectedSlotId
              ? 'Drag & drop your file here, or click to browse'
              : 'Select a requirement target above to unlock upload zone'}
          </p>
          <p className="mt-1 text-[10px] text-slate-400">
            Supported in selected slot: {allowedExtensions.join(', ')} (Max 10MB)
          </p>
        </div>
      </div>

      {/* Validation Message Panel */}
      {error && (
        <div className="rounded-lg bg-red-50 p-3.5 border border-red-100 flex items-start gap-2.5">
          {/* Error warning icon SVG */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="h-4.5 w-4.5 text-red-500 mt-0.5 shrink-0"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
            />
          </svg>
          <span className="text-xs text-red-700 leading-normal">{error}</span>
        </div>
      )}
    </div>
  );
};
