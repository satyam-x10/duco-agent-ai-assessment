import React, { useRef, useState, useEffect } from 'react';
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
  const [isOpen, setIsOpen] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Auto-advance/select the next unoccupied slot
  useEffect(() => {
    if (!selectedSlotId || occupiedSlots.includes(selectedSlotId)) {
      const nextEmptySlot = slots.find((s) => !occupiedSlots.includes(s.id));
      if (nextEmptySlot) {
        setSelectedSlotId(nextEmptySlot.id);
      } else {
        setSelectedSlotId('');
      }
    }
  }, [occupiedSlots, slots, selectedSlotId]);

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

  // Color styling configuration for each slot type to look progressive and distinct
  const slotStyles = {
    priya_pt_invoice: {
      selectBg: 'bg-blue-50/50 border-blue-200 text-blue-900 focus:ring-blue-500 focus:border-blue-500',
      dropBg: 'border-blue-300 bg-blue-50/20 text-blue-900 hover:bg-blue-50/40',
      iconColor: 'bg-blue-100 text-blue-600',
    },
    aarav_mri_report: {
      selectBg: 'bg-indigo-50/50 border-indigo-200 text-indigo-900 focus:ring-indigo-500 focus:border-indigo-500',
      dropBg: 'border-indigo-300 bg-indigo-50/20 text-indigo-900 hover:bg-indigo-50/40',
      iconColor: 'bg-indigo-100 text-indigo-600',
    },
    surgeon_estimate: {
      selectBg: 'bg-emerald-50/50 border-emerald-200 text-emerald-900 focus:ring-emerald-500 focus:border-emerald-500',
      dropBg: 'border-emerald-300 bg-emerald-50/20 text-emerald-900 hover:bg-emerald-50/40',
      iconColor: 'bg-emerald-100 text-emerald-600',
    },
    user_query_transcript: {
      selectBg: 'bg-amber-50/50 border-amber-200 text-amber-900 focus:ring-amber-500 focus:border-amber-500',
      dropBg: 'border-amber-300 bg-amber-50/20 text-amber-900 hover:bg-amber-50/40',
      iconColor: 'bg-amber-100 text-amber-600',
    },
  };

  const getSlotColors = (slotId: RequirementSlotId | '') => {
    if (slotId && slotStyles[slotId]) {
      return slotStyles[slotId];
    }
    return {
      selectBg: 'bg-white border-slate-200 text-slate-800 focus:ring-blue-500 focus:border-blue-500',
      dropBg: 'border-slate-250 bg-slate-50 hover:bg-slate-100/50',
      iconColor: 'bg-slate-100 text-slate-400',
    };
  };

  const colors = getSlotColors(selectedSlotId);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4">
        Document Upload Zone
      </h2>

      {/* Target Slot Selector */}
      <div className="mb-4 relative" ref={dropdownRef}>
        <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">
          1. Select Requirement Target
        </label>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={`w-full flex items-center justify-between rounded-lg border px-3 py-2 text-sm font-semibold focus:outline-none transition-all duration-300 cursor-pointer ${colors.selectBg}`}
        >
          <span>{currentSlot ? currentSlot.title : '-- Choose target slot --'}</span>
          <svg
            className={`h-4 w-4 text-slate-550 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>

        {isOpen && (
          <div className="absolute z-50 mt-1.5 w-full rounded-lg border border-slate-200 bg-white py-1 shadow-lg overflow-hidden animate-in fade-in slide-in-from-top-1 duration-200">
            {slots.map((s) => {
              const isFilled = occupiedSlots.includes(s.id);
              let optionStyle = 'bg-white text-slate-800 hover:bg-slate-50';
              if (s.id === 'priya_pt_invoice') optionStyle = 'bg-blue-50/30 text-blue-900 hover:bg-blue-50/60';
              if (s.id === 'aarav_mri_report') optionStyle = 'bg-indigo-50/30 text-indigo-900 hover:bg-indigo-50/60';
              if (s.id === 'surgeon_estimate') optionStyle = 'bg-emerald-50/30 text-emerald-900 hover:bg-emerald-50/60';
              if (s.id === 'user_query_transcript') optionStyle = 'bg-amber-50/30 text-amber-900 hover:bg-amber-50/60';

              return (
                <button
                  key={s.id}
                  type="button"
                  disabled={isFilled}
                  onClick={() => {
                    setSelectedSlotId(s.id);
                    setError(null);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-4 py-2 text-sm font-semibold transition-colors flex items-center justify-between ${optionStyle} ${
                    isFilled ? 'opacity-40 cursor-not-allowed bg-slate-50 text-slate-400' : 'cursor-pointer'
                  }`}
                >
                  <span>{s.title}</span>
                  {isFilled && (
                    <span className="inline-flex items-center rounded-full bg-slate-200 px-1.5 py-0.5 text-[9px] font-bold text-slate-650">
                      Occupied
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
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
          className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-all duration-300 ${
            isDragActive
              ? 'border-blue-500 bg-blue-50/10'
              : colors.dropBg
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

          {/* Dynamic Icon Wrapper */}
          <div className={`flex h-12 w-12 items-center justify-center rounded-full transition-colors duration-300 ${colors.iconColor}`}>
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

          <p className="mt-4 text-xs font-semibold">
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
