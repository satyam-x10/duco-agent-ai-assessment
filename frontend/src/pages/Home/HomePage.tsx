import React from 'react';
import { PageContainer } from '../../components/layout/PageContainer';

export const HomePage: React.FC = () => {
  return (
    <PageContainer className="max-w-4xl py-16">
      {/* App Header Info */}
      <div className="text-center">
        <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-500/10">
          v0.1.0-beta
        </span>
        <h1 className="mt-6 text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
          DuCO-Agent
        </h1>
        <p className="mt-3 text-lg text-slate-500">
          Enterprise Multi-Agent Healthcare Coordination Platform
        </p>
        <p className="mx-auto mt-6 max-w-xl text-sm leading-relaxed text-slate-400">
          An intelligent orchestration engine utilizing multi-agent collaboration to parse medical intake documents, coordinate dual-coverage insurance benefits, and draft prior authorization reviews.
        </p>
      </div>
    </PageContainer>
  );
};
