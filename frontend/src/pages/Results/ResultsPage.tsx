import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { ApiService } from '../../services/api';

// Cost Flow Visualizer Component (SVG Adjudication Chain)
const CostFlowVisualizer: React.FC<{
  billed: number;
  primaryPaid: number;
  secondaryPaid: number;
  patientOwes: number;
  primaryInsurer: string;
  secondaryInsurer: string;
}> = ({ billed, primaryPaid, secondaryPaid, patientOwes, primaryInsurer, secondaryInsurer }) => {
  return (
    <div className="flex flex-col items-center py-8 bg-slate-50/50 rounded-2xl border border-slate-200/80 shadow-inner">
      {/* Node: Provider */}
      <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-xl border border-slate-200 shadow-sm w-64 hover:translate-y-[-2px] transition-transform duration-200">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 text-lg shadow-sm">
          🏥
        </div>
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Medical Provider</h4>
          <p className="text-sm font-extrabold text-slate-800">Summit Clinic</p>
        </div>
      </div>
      
      {/* Connector 1: Provider -> Primary */}
      <div className="flex flex-col items-center my-1.5">
        <svg width="200" height="75" className="overflow-visible">
          <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
            <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
            </marker>
          </defs>
          <path d="M 100 0 L 100 65" stroke="url(#grad1)" strokeWidth="3" markerEnd="url(#arrow)" strokeDasharray="4 2" />
          <rect x="35" y="18" width="130" height="28" rx="6" fill="#eff6ff" stroke="#bfdbfe" strokeWidth="1" className="shadow-sm" />
          <text x="100" y="36" textAnchor="middle" fill="#1e3a8a" className="text-xs font-bold font-mono">
            Billed: ${billed.toFixed(2)}
          </text>
        </svg>
      </div>

      {/* Node: Primary Insurer */}
      <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-xl border border-emerald-150 shadow-sm w-64 hover:translate-y-[-2px] transition-transform duration-200 ring-1 ring-emerald-500/10">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 text-lg shadow-sm">
          🛡️
        </div>
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Primary Insurer</h4>
          <p className="text-sm font-extrabold text-slate-800">{primaryInsurer || 'Primary Plan'}</p>
        </div>
      </div>

      {/* Connector 2: Primary -> Secondary */}
      <div className="flex flex-col items-center my-1.5">
        <svg width="200" height="75" className="overflow-visible">
          <defs>
            <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#6366f1" />
            </linearGradient>
            <marker id="arrow-indigo" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#6366f1" />
            </marker>
          </defs>
          <path d="M 100 0 L 100 65" stroke="url(#grad2)" strokeWidth="3" markerEnd="url(#arrow-indigo)" strokeDasharray="4 2" />
          <rect x="35" y="18" width="130" height="28" rx="6" fill="#f0fdf4" stroke="#bbf7d0" strokeWidth="1" className="shadow-sm" />
          <text x="100" y="36" textAnchor="middle" fill="#065f46" className="text-xs font-bold font-mono">
            Paid: ${primaryPaid.toFixed(2)}
          </text>
        </svg>
      </div>

      {/* Node: Secondary Insurer */}
      <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-xl border border-indigo-150 shadow-sm w-64 hover:translate-y-[-2px] transition-transform duration-200 ring-1 ring-indigo-500/10">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 text-lg shadow-sm">
          🛡️
        </div>
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">Secondary Insurer</h4>
          <p className="text-sm font-extrabold text-slate-800">{secondaryInsurer || 'Secondary Plan'}</p>
        </div>
      </div>

      {/* Connector 3: Secondary -> Patient */}
      <div className="flex flex-col items-center my-1.5">
        <svg width="200" height="75" className="overflow-visible">
          <defs>
            <linearGradient id="grad3" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#f59e0b" />
            </linearGradient>
            <marker id="arrow-amber" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
            </marker>
          </defs>
          <path d="M 100 0 L 100 65" stroke="url(#grad3)" strokeWidth="3" markerEnd="url(#arrow-amber)" strokeDasharray="4 2" />
          <rect x="35" y="18" width="130" height="28" rx="6" fill="#e0e7ff" stroke="#c7d2fe" strokeWidth="1" className="shadow-sm" />
          <text x="100" y="36" textAnchor="middle" fill="#3730a3" className="text-xs font-bold font-mono">
            Paid: ${secondaryPaid.toFixed(2)}
          </text>
        </svg>
      </div>

      {/* Node: Patient */}
      <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-xl border border-amber-150 shadow-sm w-64 hover:translate-y-[-2px] transition-transform duration-200 ring-1 ring-amber-500/10">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600 text-lg shadow-sm">
          👤
        </div>
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-amber-700">Patient Responsibility</h4>
          <p className="text-sm font-extrabold text-slate-800">Remaining: ${patientOwes.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
};

// Expandable Pre-Auth Letters Panel
const PreAuthLettersPanel: React.FC<{ letters: any[] }> = ({ letters }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0); // First letter open by default

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Generated Prior-Authorization Requests</h3>
      
      <div className="space-y-4">
        {letters.map((letter, i) => {
          const isExpanded = expandedIndex === i;
          return (
            <div key={i} className="border border-slate-150 rounded-xl overflow-hidden shadow-sm transition-all duration-200">
              <button
                onClick={() => setExpandedIndex(isExpanded ? null : i)}
                className="w-full flex items-center justify-between bg-slate-50/40 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-800">{letter.insurer_name}</span>
                    <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 ring-1 ring-inset ring-emerald-600/10">
                      Drafted
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-450 mt-1">Policy ID: {letter.policy_id} • Generated at: {new Date(letter.generated_at).toLocaleDateString()}</p>
                </div>
                <div>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={2.5}
                    stroke="currentColor"
                    className={`h-4 w-4 text-slate-400 transition-transform duration-250 ${isExpanded ? 'rotate-180' : ''}`}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </button>
              
              {isExpanded && (
                <div className="border-t border-slate-150 bg-slate-950 p-5 font-mono text-[11px] leading-relaxed text-slate-205 overflow-x-auto whitespace-pre-wrap max-h-120 scrollbar-thin">
                  {letter.letter_content}
                </div>
              )}
            </div>
          );
        })}
        {!letters.length && (
          <div className="text-center py-6 text-slate-400">No letters generated.</div>
        )}
      </div>
    </div>
  );
};

// Main ResultsPage Component
export const ResultsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get('job_id') || 'mock-job-id';

  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await ApiService.getReportsSummary(jobId);
        setReport(data);
      } catch (err: any) {
        console.error('Failed to load reports summary:', err);
        setError('Could not retrieve benefits report summary. Please verify that intake processing has been run.');
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [jobId]);

  if (loading) {
    return (
      <PageContainer className="max-w-xl py-24 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-50 text-blue-600 shadow-sm animate-pulse mb-4">
          <svg className="animate-spin h-7 w-7" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <h2 className="text-lg font-bold text-slate-800">Fetching Adjudication Results</h2>
        <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">Compiling Agent Audits & Estimates</p>
      </PageContainer>
    );
  }

  if (error || !report) {
    return (
      <PageContainer className="max-w-xl py-24 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-rose-50 text-rose-600 shadow-sm mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-6 w-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
        </div>
        <h2 className="text-lg font-bold text-slate-800">Retrieval Failed</h2>
        <p className="text-sm text-slate-500 mt-2 px-6">{error}</p>
        <div className="mt-8 flex justify-center gap-4">
          <Link
            to="/intake"
            className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors"
          >
            Go to Intake Workspace
          </Link>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer className="max-w-7xl">
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-5 mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Benefits Coordination Results Dashboard</h1>
          <p className="text-sm text-slate-550 mt-1">
            Visualizing multi-agent adjudication pipeline, medical coding validations, and insurer details for patient:{' '}
            <strong className="text-slate-800">{report.patient_name}</strong>
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/intake"
            className="rounded-lg border border-slate-250 bg-white px-4.5 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
          >
            New Intake Run
          </Link>
        </div>
      </div>

      {/* Reviewer Warnings block */}
      {report.warnings && report.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 mb-8">
          <div className="flex gap-3">
            <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-700 mt-0.5">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-4 w-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.008v.008H12v-.008Z" />
              </svg>
            </div>
            <div>
              <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wide">Reviewer Warnings Detected</h4>
              <ul className="mt-1.5 space-y-1 list-disc pl-4 text-xs text-amber-800 leading-normal font-medium">
                {report.warnings.map((warning: string, idx: number) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Dashboard Main Grid Layout */}
      <div className="grid gap-8 lg:grid-cols-12 items-start">
        
        {/* Left Column (7/12 width) - Detailed visual panels */}
        <div className="lg:col-span-7 space-y-8">
          
          {/* Financial Breakdown Cards */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Financial Allocations Summary</h3>
            <div className="grid gap-4 sm:grid-cols-4">
              <div className="rounded-lg bg-slate-50 p-4 border border-slate-100 shadow-sm hover:scale-103 transition-transform duration-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Billed</span>
                <p className="text-xl font-extrabold text-slate-900 mt-1">
                  ${report.financial_summary.total_billed.toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg bg-blue-50/50 p-4 border border-blue-100 shadow-sm hover:scale-103 transition-transform duration-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Primary Insurer Paid</span>
                <p className="text-xl font-extrabold text-blue-700 mt-1">
                  ${report.financial_summary.primary_paid.toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg bg-indigo-50/50 p-4 border border-indigo-100 shadow-sm hover:scale-103 transition-transform duration-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">Secondary Insurer Paid</span>
                <p className="text-xl font-extrabold text-indigo-700 mt-1">
                  ${report.financial_summary.secondary_paid.toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg bg-amber-50 p-4 border border-amber-150 shadow-sm hover:scale-103 transition-transform duration-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">Patient Responsibility</span>
                <p className="text-xl font-extrabold text-amber-850 mt-1">
                  ${report.financial_summary.patient_responsibility.toFixed(2)}
                </p>
              </div>
            </div>
          </div>

          {/* Cost Flow Visual Path */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Adjudicated Claims Cost Flow</h3>
            <CostFlowVisualizer
              billed={report.financial_summary.total_billed}
              primaryPaid={report.financial_summary.primary_paid}
              secondaryPaid={report.financial_summary.secondary_paid}
              patientOwes={report.financial_summary.patient_responsibility}
              primaryInsurer={report.preauth_letters[0]?.insurer_name || 'BlueShield Cross'}
              secondaryInsurer={report.preauth_letters[1]?.insurer_name || 'UnitedHealth'}
            />
          </div>

          {/* Medical Coding Table */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Medical Coding Inference</h3>
            
            <div className="space-y-6">
              <div>
                <h4 className="text-xs font-bold text-slate-500 mb-2.5 uppercase tracking-wide">Diagnosis (ICD-10-CM)</h4>
                <div className="overflow-hidden border border-slate-150 rounded-xl">
                  <table className="min-w-full divide-y divide-slate-150 text-left text-xs">
                    <thead className="bg-slate-50/80 font-semibold text-slate-600">
                      <tr>
                        <th className="px-4 py-3">Code</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3 text-right">AI Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-800">
                      {report.coding_result?.diagnoses?.map((diag: any, i: number) => (
                        <tr key={i} className="hover:bg-slate-50/30">
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-700 ring-1 ring-inset ring-blue-700/10 font-mono">
                              {diag.code}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-700">{diag.description}</td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="h-1.5 w-16 rounded-full bg-slate-100 overflow-hidden">
                                <div className="h-full bg-emerald-500 rounded-full animate-pulse-slow" style={{ width: `${diag.confidence * 100}%` }} />
                              </div>
                              <span className="font-mono font-bold text-slate-550">{(diag.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {(!report.coding_result?.diagnoses || !report.coding_result.diagnoses.length) && (
                        <tr>
                          <td colSpan={3} className="px-4 py-6 text-center text-slate-400">No diagnosis codes found.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-slate-500 mb-2.5 uppercase tracking-wide">Procedure (CPT)</h4>
                <div className="overflow-hidden border border-slate-150 rounded-xl">
                  <table className="min-w-full divide-y divide-slate-150 text-left text-xs">
                    <thead className="bg-slate-50/80 font-semibold text-slate-600">
                      <tr>
                        <th className="px-4 py-3">Code</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3 text-right">AI Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-800">
                      {report.coding_result?.procedures?.map((proc: any, i: number) => (
                        <tr key={i} className="hover:bg-slate-50/30">
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-bold text-indigo-700 ring-1 ring-inset ring-indigo-700/10 font-mono">
                              {proc.code}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-700">{proc.description}</td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="h-1.5 w-16 rounded-full bg-slate-100 overflow-hidden">
                                <div className="h-full bg-emerald-500 rounded-full animate-pulse-slow" style={{ width: `${proc.confidence * 100}%` }} />
                              </div>
                              <span className="font-mono font-bold text-slate-550">{(proc.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {(!report.coding_result?.procedures || !report.coding_result.procedures.length) && (
                        <tr>
                          <td colSpan={3} className="px-4 py-6 text-center text-slate-400">No procedure codes found.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          {/* Pre-Authorization Letters */}
          <PreAuthLettersPanel letters={report.letters} />

        </div>

        {/* Right Column (5/12 width) - Timeline & pipeline tracking */}
        <div className="lg:col-span-5 space-y-8">
          
          {/* Workflow Summary Checklist */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Adjudication Progress Timeline</h3>
            
            <div className="space-y-3.5">
              {Object.entries(report.workflow_summary || {}).map(([step, completed], i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                    completed 
                      ? 'bg-emerald-50 border-emerald-500 text-emerald-600 shadow-sm' 
                      : 'border-slate-200 text-slate-300'
                  }`}>
                    {completed ? (
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor" className="h-3 w-3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                    ) : (
                      <div className="h-1.5 w-1.5 rounded-full bg-slate-350" />
                    )}
                  </div>
                  <span className={`text-xs font-semibold ${completed ? 'text-slate-800 font-bold' : 'text-slate-400'}`}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Workflow Trace Timeline */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Agent Execution Trace Log</h3>
            
            <div className="relative border-l border-slate-150 pl-5 ml-2.5 space-y-6 text-xs">
              {report.trace?.map((entry: any, i: number) => (
                <div key={i} className="relative">
                  {/* Timeline bullet bullet marker */}
                  <div className="absolute -left-7.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm ring-4 ring-white">
                    <span className={`h-2.5 w-2.5 rounded-full ${
                      entry.status === 'success' ? 'bg-emerald-500 animate-pulse-slow' : 'bg-rose-500'
                    }`} />
                  </div>
                  
                  <div className="space-y-1.5 bg-slate-50/40 border border-slate-100 rounded-xl p-3 shadow-sm hover:scale-[1.01] transition-transform duration-200">
                    <div className="flex items-center justify-between">
                      <span className="font-extrabold text-slate-800">{entry.agent_name}</span>
                      <span className="text-[10px] text-slate-400 font-mono font-semibold">
                        {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <div>
                      <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[9px] font-bold tracking-wide uppercase ${
                        entry.status === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                      }`}>
                        {entry.status}
                      </span>
                    </div>
                    <p className="text-slate-550 leading-relaxed font-medium mt-1">{entry.message}</p>
                  </div>
                </div>
              ))}
              {(!report.trace || !report.trace.length) && (
                <div className="text-center py-6 text-slate-400">No agent trace logs recorded.</div>
              )}
            </div>
          </div>

          {/* Audio stream briefings summary briefing streamer card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Briefing Audio Streamer</h3>
            
            <div className="rounded-xl border border-slate-150 p-4.5 bg-slate-50/50 text-center shadow-sm">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-blue-50 text-blue-600 mb-2.5 shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-5.5 w-5.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
                </svg>
              </div>
              <span className="text-xs font-bold text-slate-800">TTS Audio Adjudication Briefing</span>
              <p className="text-[10px] text-slate-400 mt-1.5 font-semibold">Duration: {report.audio_briefing?.estimated_duration_seconds || '78.5'}s</p>

              <button
                type="button"
                className="mt-3.5 rounded-lg border border-slate-200 bg-white px-4 py-1.5 text-xs font-bold text-slate-700 shadow-sm hover:bg-slate-50 transition-colors w-full cursor-pointer"
              >
                Play Audio Briefing (Demo Only)
              </button>
            </div>

            {/* Patient Briefing Narration Script */}
            {report.audio_briefing && (
              <div className="mt-6 border-t border-slate-150 pt-5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-450 mb-3 flex items-center justify-between">
                  <span>Patient Briefing Script</span>
                  <span className="text-[9px] font-semibold text-blue-650 bg-blue-50 px-1.5 py-0.5 rounded">Future TTS Ready</span>
                </h4>
                <div className="space-y-3.5 text-xs">
                  {report.audio_briefing.sections.map((section: any, idx: number) => (
                    <div key={idx} className="bg-slate-50/50 rounded-xl p-3 border border-slate-100">
                      <span className="font-extrabold text-slate-700 block text-[10px] uppercase tracking-wide mb-1">
                        {section.title}
                      </span>
                      <p className="text-slate-600 leading-relaxed font-medium">{section.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </PageContainer>
  );
};
