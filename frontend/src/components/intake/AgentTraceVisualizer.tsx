import React from 'react';

export interface TraceEntry {
  agent_name: string;
  status: string;
  message: string;
  timestamp: string;
}

export interface AgentTraceVisualizerProps {
  traces: TraceEntry[];
  currentAgent?: string | null;
  judgeEvaluation?: {
    quality_score: number;
    passed: boolean;
    critique: string;
    recommended_action: string;
  } | null;
}

export const AgentTraceVisualizer: React.FC<AgentTraceVisualizerProps> = ({
  traces,
  currentAgent,
  judgeEvaluation,
}) => {
  const getAgentBadgeColor = (name: string) => {
    switch (name) {
      case 'IntakeAgent':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'DocIntelAgent':
        return 'bg-indigo-100 text-indigo-800 border-indigo-300';
      case 'MedicalCodingAgent':
        return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'InsuranceAgent':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'COBAgent':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'FinanceAgent':
        return 'bg-teal-100 text-teal-800 border-teal-300';
      case 'ReviewerAgent':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'JudgeAgent':
        return 'bg-violet-100 text-violet-800 border-violet-300 font-bold';
      case 'ClinicianAuditor':
        return 'bg-cyan-100 text-cyan-800 border-cyan-300 font-semibold';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getStatusIcon = (status: string) => {
    if (status === 'success') return '✅';
    if (status === 'retry') return '🔄';
    if (status === 'error') return '❌';
    return '⚡';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mb-6">
      <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2">
          <span className="text-xl">🗺️</span>
          <h3 className="font-semibold text-slate-800 text-lg">Agent Orchestration Traces</h3>
          <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono">
            ADK Dynamic Planner
          </span>
        </div>
        {judgeEvaluation && (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-500 font-medium">LLM Judge Score:</span>
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                judgeEvaluation.passed
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-rose-100 text-rose-800 border border-rose-300'
              }`}
            >
              {judgeEvaluation.quality_score}/100 ({judgeEvaluation.recommended_action})
            </span>
          </div>
        )}
      </div>

      {currentAgent && (
        <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center space-x-3 animate-pulse">
          <div className="w-3 h-3 rounded-full bg-amber-500 animate-ping" />
          <span className="text-sm font-medium text-amber-900">
            Currently Executing: <strong className="font-bold">{currentAgent}</strong>
          </span>
        </div>
      )}

      {traces.length === 0 ? (
        <p className="text-sm text-slate-500 italic py-3 text-center">No trace events recorded yet. Start analysis to view live agent step logs.</p>
      ) : (
        <div className="relative border-l-2 border-slate-200 ml-4 space-y-4 py-2">
          {traces.map((trace, idx) => (
            <div key={idx} className="relative pl-6">
              <span className="absolute -left-[9px] top-1 w-4 h-4 rounded-full bg-white border-2 border-indigo-600 flex items-center justify-center text-[10px]">
                {getStatusIcon(trace.status)}
              </span>

              <div className="flex items-start justify-between">
                <div>
                  <span className={`inline-block px-2.5 py-0.5 rounded-md text-xs border ${getAgentBadgeColor(trace.agent_name)}`}>
                    {trace.agent_name}
                  </span>
                  <span className="ml-2 text-xs font-mono text-slate-400">
                    {trace.timestamp ? new Date(trace.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>
                <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
                  {trace.status}
                </span>
              </div>

              <p className="text-sm text-slate-700 mt-1 bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-mono text-xs">
                {trace.message}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
