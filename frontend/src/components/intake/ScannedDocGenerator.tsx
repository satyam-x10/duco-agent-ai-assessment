import React, { useState } from 'react';
import { ApiService } from '../../services/api';

export interface ScannedDocGeneratorProps {
  onDocumentGenerated?: (filename: string) => void;
}

export const ScannedDocGenerator: React.FC<ScannedDocGeneratorProps> = ({ onDocumentGenerated }) => {
  const [loading, setLoading] = useState(false);
  const [docCategory, setDocCategory] = useState('Surgeon Cost Estimate');
  const [patientName, setPatientName] = useState('Priya Sen');
  const [cptCode, setCptCode] = useState('29881');
  const [amount, setAmount] = useState(3200);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccessMessage(null);
    try {
      const res = await ApiService.generateScannedDocument({
        title: 'SUMMIT MEDICAL CENTER',
        document_category: docCategory,
        patient_name: patientName,
        member_id: 'MEM-882194',
        cpt_code: cptCode,
        cpt_desc: 'Knee Arthroscopy with Meniscectomy',
        estimated_amount: amount,
      });

      setSuccessMessage(`Scanned document '${res.filename}' generated with scan rotation and noise artifacts.`);
      if (onDocumentGenerated) {
        onDocumentGenerated(res.filename);
      }
    } catch (err) {
      console.error('Failed to generate scanned document:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-50 rounded-xl border border-slate-200 p-5 mb-6 shadow-sm">
      <div className="flex items-center space-x-2 mb-3">
        <span className="text-xl">🖨️</span>
        <h3 className="font-bold text-slate-800 text-base">GCP Playground Scanned Document Generator</h3>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Generates realistic synthetic scanned medical notes, invoices, and insurance documents with simulated OCR scan noise, rotation, and stamps.
      </p>

      <form onSubmit={handleGenerate} className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
        <div>
          <label className="block text-[11px] font-semibold text-slate-800 mb-1">Document Type</label>
          <select
            value={docCategory}
            onChange={(e) => setDocCategory(e.target.value)}
            className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white text-black font-medium"
          >
            <option value="Surgeon Cost Estimate" className="text-black">Surgeon Cost Estimate</option>
            <option value="Physical Therapy Invoice" className="text-black">Physical Therapy Invoice</option>
            <option value="MRI Diagnostic Report" className="text-black">MRI Diagnostic Report</option>
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-800 mb-1">Patient Name</label>
          <input
            type="text"
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white text-black font-medium"
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-800 mb-1">CPT Code</label>
          <input
            type="text"
            value={cptCode}
            onChange={(e) => setCptCode(e.target.value)}
            className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white text-black font-mono font-medium"
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-800 mb-1">Billed Amount ($)</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className="w-full text-xs p-2 border border-slate-300 rounded-lg bg-white text-black font-mono font-medium"
          />
        </div>

        <div className="md:col-span-4 flex items-center justify-end pt-2">
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700 disabled:opacity-50 transition-colors cursor-pointer"
          >
            {loading ? 'Generating Synthetic Scan...' : '✨ Generate Synthetic Scanned Document'}
          </button>
        </div>
      </form>

      {successMessage && (
        <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 font-medium">
          ✅ {successMessage}
        </div>
      )}
    </div>
  );
};
