import React, { useState, useEffect, useRef } from 'react';

export interface LogMessage {
  agent_name: string;
  status: string;
  message: string;
  timestamp: string;
  progress?: number;
}

export interface AgentLogStreamerProps {
  jobId: string | null;
  isStreaming?: boolean;
}

export const AgentLogStreamer: React.FC<AgentLogStreamerProps> = ({ jobId, isStreaming = false }) => {
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [filter, setFilter] = useState<'ALL' | 'RETRY' | 'JUDGE'>('ALL');
  const [connected, setConnected] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!jobId || !isStreaming) return;

    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    const eventSource = new EventSource(`${apiBase}/analysis/stream/${jobId}`);

    setConnected(true);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.message === 'STREAM_FINISHED') {
          eventSource.close();
          setConnected(false);
          return;
        }

        setLogs((prev) => [...prev, data]);
      } catch (err) {
        console.error('Failed to parse SSE event payload:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.warn('SSE EventSource disconnected:', err);
      eventSource.close();
      setConnected(false);
    };

    return () => {
      eventSource.close();
      setConnected(false);
    };
  }, [jobId, isStreaming]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const filteredLogs = logs.filter((log) => {
    if (filter === 'RETRY') return log.status === 'retry';
    if (filter === 'JUDGE') return log.agent_name === 'JudgeAgent' || log.agent_name === 'Orchestrator';
    return true;
  });

  return (
    <div className="bg-slate-900 text-slate-100 rounded-xl shadow-lg border border-slate-800 p-4 mb-6 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <div className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-emerald-500 animate-ping' : 'bg-slate-600'}`} />
          <span className="font-bold text-slate-200">Parsed Agent Log Stream</span>
          <span className="text-[10px] text-slate-500 uppercase tracking-widest bg-slate-800 px-2 py-0.5 rounded">
            {connected ? 'LIVE SSE STREAM' : 'LOG CONSOLE'}
          </span>
        </div>

        <div className="flex items-center space-x-1.5 bg-slate-800 p-1 rounded-md">
          <button
            onClick={() => setFilter('ALL')}
            className={`px-2 py-1 rounded text-[11px] ${filter === 'ALL' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'}`}
          >
            All Logs
          </button>
          <button
            onClick={() => setFilter('RETRY')}
            className={`px-2 py-1 rounded text-[11px] ${filter === 'RETRY' ? 'bg-amber-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Retries
          </button>
          <button
            onClick={() => setFilter('JUDGE')}
            className={`px-2 py-1 rounded text-[11px] ${filter === 'JUDGE' ? 'bg-purple-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Judge Decisions
          </button>
        </div>
      </div>

      <div className="h-48 overflow-y-auto space-y-1.5 pr-2 custom-scrollbar">
        {filteredLogs.length === 0 ? (
          <div className="text-slate-600 italic text-center py-8">
            Waiting for agent log stream events...
          </div>
        ) : (
          filteredLogs.map((log, i) => (
            <div key={i} className="flex items-start space-x-2 hover:bg-slate-800/60 p-1 rounded">
              <span className="text-slate-500 shrink-0">[{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'LOG'}]</span>
              <span className="text-cyan-400 font-bold shrink-0">[{log.agent_name}]</span>
              <span className={log.status === 'retry' ? 'text-amber-400 font-bold' : log.status === 'error' ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};
