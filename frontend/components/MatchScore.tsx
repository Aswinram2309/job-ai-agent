'use client';

import React from 'react';

export default function MatchScore({ score }: { score: number }) {
  let colorStyles = 'bg-slate-800 text-slate-300 border-slate-700';
  let dotColor = 'bg-slate-400';

  if (score >= 75) {
    colorStyles = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    dotColor = 'bg-emerald-400';
  } else if (score >= 50) {
    colorStyles = 'bg-amber-500/15 text-amber-400 border-amber-500/30';
    dotColor = 'bg-amber-400';
  }

  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${colorStyles}`}>
      <span className={`w-2 h-2 rounded-full ${dotColor}`} />
      <span>{score.toFixed(0)}% Match</span>
    </div>
  );
}
