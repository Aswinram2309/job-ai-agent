'use client';

import React from 'react';
import { Job, JobMatchResult } from '../types';
import MatchScore from './MatchScore';
import { ExternalLink, MapPin, Building, Clock, ArrowRight, ShieldCheck } from 'lucide-react';

interface JobCardProps {
  jobMatch?: JobMatchResult;
  job?: Job;
  onApplyClick: (targetJob: Job) => void;
  onQuickApply?: (targetJob: Job) => void;
  applyingJobId?: string | null;
}

export default function JobCard({ jobMatch, job, onApplyClick, onQuickApply, applyingJobId }: JobCardProps) {
  const currentJob = jobMatch?.job || job;
  if (!currentJob) return null;

  const score = jobMatch?.match_score;
  const matchingSkills = jobMatch?.matching_skills || [];
  const missingSkills = jobMatch?.missing_requirements || [];
  const reasons = jobMatch?.reasons || [];
  const isApplying = applyingJobId === currentJob.id;

  return (
    <div className="bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 rounded-3xl p-6 transition-all hover:shadow-xl hover:shadow-black/20 backdrop-blur-sm flex flex-col justify-between group">
      <div>
        {/* Header with Title and Match Score */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-brand-400 bg-brand-500/10 px-2.5 py-0.5 rounded-md border border-brand-500/20 mb-2 inline-block">
              {currentJob.provider}
            </span>
            <h3 className="text-base md:text-lg font-bold text-white group-hover:text-brand-300 transition-colors">
              {currentJob.title}
            </h3>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span className="flex items-center gap-1 font-medium text-slate-300">
                <Building className="w-3.5 h-3.5 text-slate-500" />
                {currentJob.company}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                {currentJob.location || 'Remote'}
              </span>
              {currentJob.job_type && (
                <span className="hidden sm:inline-block bg-slate-800 px-2 py-0.5 rounded text-[11px] border border-slate-700">
                  {currentJob.job_type}
                </span>
              )}
            </div>
          </div>

          {score !== undefined && <MatchScore score={score} />}
        </div>

        {/* Salary only when available */}
        {currentJob.salary && (
          <div className="mb-3 text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg inline-block">
            {currentJob.salary}
          </div>
        )}

        {/* Match Reasons */}
        {reasons.length > 0 && (
          <div className="my-3 p-3 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-300 space-y-1">
            <span className="font-semibold text-slate-400 block text-[11px] uppercase tracking-wider">Alignment Breakdown</span>
            {reasons.slice(0, 2).map((r, i) => (
              <p key={i} className="text-slate-300/90 leading-relaxed">• {r}</p>
            ))}
          </div>
        )}

        {/* Skills pill list */}
        <div className="my-4 space-y-2">
          {matchingSkills.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-[11px] text-slate-400 font-medium mr-1">Matching:</span>
              {matchingSkills.slice(0, 4).map((skill, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-medium text-[11px]"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}

          {missingSkills.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-[11px] text-slate-400 font-medium mr-1">Missing:</span>
              {missingSkills.slice(0, 3).map((skill, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-300 font-medium text-[11px]"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs">
        <a
          href={currentJob.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-slate-400 hover:text-brand-300 transition-colors font-medium text-[11px]"
        >
          <span>Official Portal</span>
          <ExternalLink className="w-3 h-3" />
        </a>

        <div className="flex items-center gap-2">
          {onQuickApply && (
            <button
              onClick={() => onQuickApply(currentJob)}
              disabled={isApplying}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold transition-all shadow-md shadow-emerald-900/30 disabled:opacity-50"
            >
              <span>{isApplying ? 'Applying...' : '⚡ 1-Click Apply'}</span>
            </button>
          )}

          <button
            onClick={() => onApplyClick(currentJob)}
            className="flex items-center gap-1 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition-all"
          >
            <span>Review</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
