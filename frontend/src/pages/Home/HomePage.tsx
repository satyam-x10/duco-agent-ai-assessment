import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="relative bg-slate-900 text-white min-h-[calc(100vh-4rem)] flex flex-col justify-center items-center">
      {/* Soft ambient background glow */}
      <div className="absolute top-[25%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] rounded-full bg-blue-600/10 blur-[100px] pointer-events-none" />

      <PageContainer className="relative z-10 max-w-3xl mx-auto px-4 text-center space-y-8">
        {/* Version Badge */}
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400 ring-1 ring-inset ring-blue-400/20">
            v1.0.0
          </span>
        </div>

        {/* Title & Description */}
        <div className="space-y-4">
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white">
            DuCO-Agent
          </h1>
          <p className="text-lg sm:text-xl font-medium text-slate-300">
            Enterprise Multi-Agent Healthcare Coordination
          </p>
          <p className="text-sm sm:text-base text-slate-400 max-w-xl mx-auto leading-relaxed">
            An orchestration engine utilizing 7 specialist AI agents to parse medical intake documents, coordinate dual-coverage benefits, and draft prior authorization reviews.
          </p>
        </div>

        {/* Call to Actions */}
        <div className="flex justify-center gap-4">
          <button
            onClick={() => navigate('/intake')}
            className="px-6 py-3 rounded-lg font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
          >
            Open Workspace
          </button>
          <button
            onClick={() => navigate('/results')}
            className="px-6 py-3 rounded-lg font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/50 transition-colors cursor-pointer"
          >
            View Results
          </button>
        </div>

        {/* Minimal Pipeline Agent List */}
        <div className="pt-12 border-t border-slate-800/60">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-6">
            ADK Pipeline Sequence
          </p>
          <div className="flex flex-wrap justify-center gap-4 text-xs text-slate-300">
            {[
              { label: 'Intake', emoji: '📋' },
              { label: 'DocIntel', emoji: '🔍' },
              { label: 'Medical Coding', emoji: '🧬' },
              { label: 'Insurance', emoji: '🏥' },
              { label: 'COB Rules', emoji: '⚖️' },
              { label: 'Finance Ledger', emoji: '💰' },
              { label: 'Reviewer Audit', emoji: '🔎' }
            ].map((agent, index) => (
              <div 
                key={index} 
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800/40 border border-slate-800"
              >
                <span>{agent.emoji}</span>
                <span className="font-medium text-slate-400">{agent.label}</span>
              </div>
            ))}
          </div>
        </div>
      </PageContainer>
    </div>
  );
};
