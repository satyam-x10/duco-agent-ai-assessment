import React, { useState } from 'react';

export interface HumanInTheLoopCardProps {
  jobId: string;
  warnings?: string[];
  judgeEvaluation?: {
    quality_score: number;
    critique: string;
    recommended_action: string;
  } | null;
  onApprove: () => void;
  onOverride: (overrideData: { diagnoses?: { code: string; description: string }[]; procedures?: { code: string; description: string }[] }) => void;
}

export const HumanInTheLoopCard: React.FC<HumanInTheLoopCardProps> = ({
  jobId: _jobId,
  warnings = [],
  judgeEvaluation,
  onApprove,
  onOverride,
}) => {
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [icdCode, setIcdCode] = useState('M25.561');
  const [icdDesc, setIcdDesc] = useState('Pain in right knee');
  const [cptCode, setCptCode] = useState('73721');
  const [cptDesc, setCptDesc] = useState('Magnetic resonance imaging, knee joint');

  const handleOverrideSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onOverride({
      diagnoses: [{ code: icdCode, description: icdDesc }],
      procedures: [{ code: cptCode, description: cptDesc }],
    });
    setShowOverrideModal(false);
  };

  return (
    <div className="bg-amber-50 border-2 border-amber-400 rounded-xl p-5 mb-6 shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-amber-500 text-white flex items-center justify-center text-xl font-bold">
            ✋
          </div>
          <div>
            <h3 className="font-bold text-amber-900 text-lg">Human-in-the-Loop Audit Approval Required</h3>
            <p className="text-xs text-amber-700">
              The automated agent pipeline paused due to low confidence or clinical policy flags. Clinician auditor sign-off is required to proceed.
            </p>
          </div>
        </div>

        <span className="bg-amber-200 text-amber-900 font-mono text-xs px-2.5 py-1 rounded-md font-bold uppercase">
          AWAITING CLINICIAN REVIEW
        </span>
      </div>

      {judgeEvaluation && (
        <div className="mt-4 bg-white/80 p-3.5 rounded-lg border border-amber-200">
          <div className="flex items-center justify-between text-xs font-semibold text-amber-900 mb-1">
            <span>LLM-as-a-Judge Verdict:</span>
            <span className="font-mono bg-amber-100 px-2 py-0.5 rounded">Score {judgeEvaluation.quality_score}/100</span>
          </div>
          <p className="text-xs text-amber-800 italic">"{judgeEvaluation.critique}"</p>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="mt-3 space-y-1">
          <span className="text-xs font-bold text-amber-900">Flagged Audit Warnings:</span>
          <ul className="list-disc list-inside text-xs text-amber-800 space-y-1">
            {warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-5 flex items-center justify-end space-x-3">
        <button
          onClick={() => setShowOverrideModal(true)}
          className="px-4 py-2 bg-white border border-amber-300 text-amber-900 rounded-lg text-sm font-semibold hover:bg-amber-100 transition-colors shadow-sm"
        >
          ✏️ Edit / Override Medical Codes
        </button>

        <button
          onClick={onApprove}
          className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-sm font-bold hover:bg-emerald-700 transition-colors shadow-sm"
        >
          Sign-Off & Approve Claim
        </button>
      </div>

      {showOverrideModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <h4 className="font-bold text-slate-800 text-lg mb-2">Override Medical Codes (HITL)</h4>
            <p className="text-xs text-slate-500 mb-4">
              Manually supply validated ICD-10 diagnosis codes and CPT procedure codes to override low confidence extractions.
            </p>

            <form onSubmit={handleOverrideSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">ICD-10 Diagnosis Code</label>
                <input
                  type="text"
                  value={icdCode}
                  onChange={(e) => setIcdCode(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Diagnosis Description</label>
                <input
                  type="text"
                  value={icdDesc}
                  onChange={(e) => setIcdDesc(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">CPT Procedure Code</label>
                <input
                  type="text"
                  value={cptCode}
                  onChange={(e) => setCptCode(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Procedure Description</label>
                <input
                  type="text"
                  value={cptDesc}
                  onChange={(e) => setCptDesc(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowOverrideModal(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-bold hover:bg-amber-700 shadow-sm"
                >
                  Apply Override & Resume
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
