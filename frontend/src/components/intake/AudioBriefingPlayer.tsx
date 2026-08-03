import React, { useState, useEffect } from 'react';
import { ApiService } from '../../services/api';

export interface AudioBriefingPlayerProps {
  jobId: string;
}

export interface AudioBriefingData {
  patient_name: string;
  full_narration: string;
  estimated_duration_seconds: number;
  sections: { title: string; text: string }[];
}

export const AudioBriefingPlayer: React.FC<AudioBriefingPlayerProps> = ({ jobId }) => {
  const [briefing, setBriefing] = useState<AudioBriefingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    const loadAudioBriefing = async () => {
      setLoading(true);
      try {
        const response = await ApiService.fetchAudioBriefing(jobId);
        if (response && response.briefing) {
          setBriefing(response.briefing);
        }
      } catch (err) {
        console.error('Failed to load audio briefing:', err);
      } finally {
        setLoading(false);
      }
    };

    loadAudioBriefing();

    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [jobId]);

  const togglePlaySpeech = () => {
    if (!briefing || !window.speechSynthesis) return;

    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
    } else {
      const utterance = new SpeechSynthesisUtterance(briefing.full_narration);
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);
      setIsPlaying(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  if (loading) {
    return (
      <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-6 text-center text-xs text-indigo-700 animate-pulse">
        Generating Text-to-Speech final verdict narration audio briefing...
      </div>
    );
  }

  if (!briefing) return null;

  return (
    <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-purple-900 text-white rounded-xl shadow-lg p-5 mb-6 border border-indigo-700">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-indigo-500/30 border border-indigo-400/40 flex items-center justify-center text-xl">
            🎙️
          </div>
          <div>
            <h3 className="font-bold text-lg leading-tight">Patient Audio Briefing Narration</h3>
            <p className="text-xs text-indigo-200">
              Final Verdict Summary for {briefing.patient_name} (~{briefing.estimated_duration_seconds} sec)
            </p>
          </div>
        </div>

        <button
          onClick={togglePlaySpeech}
          className={`px-5 py-2.5 rounded-lg text-sm font-bold flex items-center space-x-2 transition-all shadow-md ${
            isPlaying
              ? 'bg-rose-500 hover:bg-rose-600 text-white'
              : 'bg-emerald-500 hover:bg-emerald-600 text-white'
          }`}
        >
          <span>{isPlaying ? '⏸️ Pause Narration' : '▶️ Listen to Verdict Audio'}</span>
        </button>
      </div>

      <div className="mt-3 bg-indigo-950/50 p-3.5 rounded-lg border border-indigo-700/50 text-xs text-indigo-100 max-h-32 overflow-y-auto leading-relaxed">
        <span className="font-bold text-indigo-300 block mb-1 uppercase tracking-wider text-[10px]">Spoken Verdict Transcript:</span>
        {briefing.full_narration}
      </div>
    </div>
  );
};
