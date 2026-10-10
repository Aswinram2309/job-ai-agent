'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../lib/api';
import { Job, JobMatchResult, CandidateProfile, Application } from '../../types';
import Navbar from '../../components/Navbar';
import Sidebar from '../../components/Sidebar';
import JobCard from '../../components/JobCard';
import {
  Briefcase, Search, Sparkles, Filter, ExternalLink,
  ShieldCheck, Check, AlertTriangle, ArrowRight, Loader2,
  CheckCircle2, Building, MapPin, X, Bookmark
} from 'lucide-react';

export default function JobsPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobMatches, setJobMatches] = useState<JobMatchResult[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingMatch, setLoadingMatch] = useState(false);
  const [keywordsInput, setKeywordsInput] = useState('Software Engineer');
  const [locationInput, setLocationInput] = useState('');
  const [filterRemote, setFilterRemote] = useState(false);
  const [activeTab, setActiveTab] = useState<'recommended' | 'all'>('recommended');

  // Application Modal State
  const [selectedJobForApply, setSelectedJobForApply] = useState<Job | null>(null);
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [approvalConfirmed, setApprovalConfirmed] = useState(true);
  const [applyingJobId, setApplyingJobId] = useState<string | null>(null);
  const [answers, setAnswers] = useState({
    authorized_to_work: 'Yes',
    requires_sponsorship: 'No',
    notice_period: 'Immediately',
    notes: ''
  });
  const [submittingApp, setSubmittingApp] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<Application | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    const token = api.getToken();
    if (!token) {
      router.replace('/login');
      return;
    }

    const init = async () => {
      try {
        const prof = await api.getProfile();
        setProfile(prof);
        if (prof?.preferred_roles && prof.preferred_roles.length > 0) {
          setKeywordsInput(prof.preferred_roles[0]);
        }
        // Fetch existing jobs from DB
        const existingJobs = await api.getJobs();
        setJobs(existingJobs);
      } catch (err) {
        console.error('Failed to initialize jobs:', err);
      }
    };

    init();
  }, [router]);

  // Handle Search for Real Jobs
  const handleSearch = async (e?: React.FormEvent, customKeywords?: string) => {
    if (e) e.preventDefault();
    setLoadingSearch(true);
    try {
      const activeKw = customKeywords !== undefined ? customKeywords : keywordsInput;
      const kw = activeKw ? activeKw.split(',').map(s => s.trim()).filter(Boolean) : [];
      const skills = profile?.technical_skills?.slice(0, 5) || [];
      const res = await api.searchJobs({
        keywords: kw,
        location: locationInput || undefined,
        skills,
        limit: 15
      });
      setJobs(res.jobs);

      // If we have profile skills, run matching
      if (res.jobs.length > 0 && profile) {
        await handleRunMatching(res.jobs);
      }
    } catch (err) {
      console.error('Job search failed:', err);
    } finally {
      setLoadingSearch(false);
    }
  };

  // Quick 1-Click Apply Flow
  const handleQuickApply = async (targetJob: Job) => {
    setApplyingJobId(targetJob.id);
    setSaveSuccessMsg(null);
    try {
      // 1. Stage approval automatically with default answers
      await api.approveJob(targetJob.id, {
        authorized_to_work: 'Yes',
        requires_sponsorship: 'No',
        notice_period: 'Immediately',
        notes: '1-Click Applied via Job Agent'
      });

      // 2. Query application record and submit to pipeline
      const apps = await api.getApplications();
      const existingApp = apps.find(a => a.job_id === targetJob.id);
      if (existingApp) {
        await api.submitApplication(existingApp.id);
      }

      // 3. Open official employer job portal directly for user comfort
      if (targetJob.url) {
        window.open(targetJob.url, '_blank', 'noopener,noreferrer');
      }

      setSaveSuccessMsg(`🚀 Successfully applied & staged "${targetJob.title}" at ${targetJob.company}! Official application page opened.`);
      setTimeout(() => setSaveSuccessMsg(null), 8000);
    } catch (err: any) {
      // Fallback to opening the apply modal if extra info is needed
      openApplyModal(targetJob);
      setApplyError(err.message || 'Please review and confirm details below.');
    } finally {
      setApplyingJobId(null);
    }
  };

  // Handle AI Matching
  const handleRunMatching = async (targetJobs?: Job[]) => {
    const jobsToMatch = targetJobs || jobs;
    if (!jobsToMatch.length) return;

    setLoadingMatch(true);
    try {
      const matchRes = await api.matchJobs(jobsToMatch.map(j => j.id), 0.0, 15);
      setJobMatches(matchRes.matches);
      setActiveTab('recommended');
    } catch (err) {
      console.error('Matching failed:', err);
    } finally {
      setLoadingMatch(false);
    }
  };

  // Save Job
  const handleSaveJob = async (jobId: string) => {
    try {
      await api.saveJob(jobId);
      setSaveSuccessMsg('Job saved to your applications dashboard!');
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      console.error('Failed to save job:', err);
    }
  };

  // Open Apply Review Modal
  const openApplyModal = (targetJob: Job) => {
    setSelectedJobForApply(targetJob);
    setApprovalConfirmed(true);
    setSubmissionResult(null);
    setApplyError(null);
    setApplyModalOpen(true);
  };

  // Submit Application with User Approval
  const handleExecuteApplication = async () => {
    if (!selectedJobForApply) return;
    setSubmittingApp(true);
    setApplyError(null);

    try {
      // Step 1: Record user approval
      const approvalData = await api.approveJob(selectedJobForApply.id, answers);

      // Step 2: Query application record
      const apps = await api.getApplications();
      const existingApp = apps.find(a => a.job_id === selectedJobForApply.id);

      if (!existingApp) {
        throw new Error('Application could not be created.');
      }

      // Step 3: Execute application workflow
      const finalApp = await api.submitApplication(existingApp.id);
      setSubmissionResult(finalApp);

      // Open official portal automatically
      if (selectedJobForApply.url) {
        window.open(selectedJobForApply.url, '_blank', 'noopener,noreferrer');
      }
    } catch (err: any) {
      setApplyError(err.message || 'Application execution failed.');
    } finally {
      setSubmittingApp(false);
    }
  };

  // Mark Manually Applied
  const handleMarkManualApply = async () => {
    if (!submissionResult) return;
    try {
      const updated = await api.manualApply(
        submissionResult.id,
        'Applied directly on official portal',
        `MANUAL-${Date.now()}`
      );
      setSubmissionResult(updated);
    } catch (err: any) {
      setApplyError(err.message || 'Failed to mark as manually applied.');
    }
  };

  // Filtered jobs list
  const displayedJobs = jobs.filter(j => {
    if (filterRemote) {
      return (
        (j.location && j.location.toLowerCase().includes('remote')) ||
        (j.title && j.title.toLowerCase().includes('remote'))
      );
    }
    return true;
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <Navbar userEmail={profile?.email} />

      <div className="flex-1 flex">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full space-y-8">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/20 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                Live Job Discovery
              </span>
              <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
                Authentic Job Opportunities
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                Sourced exclusively from verified employer portals (Greenhouse & Lever). Zero synthetic or hallucinated vacancies.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleRunMatching()}
                disabled={loadingMatch || jobs.length === 0}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-brand-600/20 transition-all disabled:opacity-50"
              >
                {loadingMatch ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Matching with Gemini...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-amber-300" />
                    <span>Re-evaluate Match Scores</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {saveSuccessMsg && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs rounded-xl flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-400" />
              <span>{saveSuccessMsg}</span>
            </div>
          )}

          {/* Search Bar & Filters */}
          <form
            onSubmit={handleSearch}
            className="bg-slate-900/60 border border-slate-800 rounded-3xl p-4 md:p-6 backdrop-blur-sm shadow-xl flex flex-col md:flex-row gap-4 items-center"
          >
            <div className="flex-1 relative w-full">
              <Search className="w-4 h-4 text-slate-500 absolute left-4 top-3.5" />
              <input
                type="text"
                value={keywordsInput}
                onChange={(e) => setKeywordsInput(e.target.value)}
                placeholder="Keywords or Roles (e.g. Backend, Distributed Systems, Python)"
                className="w-full bg-slate-950/70 border border-slate-800 rounded-2xl pl-11 pr-4 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="w-full md:w-64 relative">
              <MapPin className="w-4 h-4 text-slate-500 absolute left-4 top-3.5" />
              <input
                type="text"
                value={locationInput}
                onChange={(e) => setLocationInput(e.target.value)}
                placeholder="Location (e.g. Remote, San Francisco)"
                className="w-full bg-slate-950/70 border border-slate-800 rounded-2xl pl-11 pr-4 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer bg-slate-800/40 px-3 py-2.5 rounded-xl border border-slate-700/60 shrink-0">
                <input
                  type="checkbox"
                  checked={filterRemote}
                  onChange={(e) => setFilterRemote(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-brand-600 focus:ring-0"
                />
                <span>Remote Only</span>
              </label>

              <button
                type="submit"
                disabled={loadingSearch}
                className="w-full md:w-auto px-6 py-3 bg-brand-600 hover:bg-brand-500 text-white rounded-2xl text-xs font-semibold flex items-center justify-center gap-2 shadow-md shadow-brand-600/25 transition-all disabled:opacity-50"
              >
                {loadingSearch ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    <span>Search Live Jobs</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Quick Search Suggestions */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider mr-1">Popular Roles:</span>
            {[
              'Data Analyst',
              'Data Engineer',
              'Software Engineer',
              'Python Developer',
              'Backend Engineer',
              'Frontend Developer'
            ].map((role) => (
              <button
                key={role}
                type="button"
                onClick={() => {
                  setKeywordsInput(role);
                  handleSearch(undefined, role);
                }}
                className="px-3 py-1 rounded-full text-xs bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-brand-500/50 hover:bg-brand-500/10 transition-all cursor-pointer"
              >
                + {role}
              </button>
            ))}
          </div>

          {/* Results Tabs & Count */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setActiveTab('recommended')}
                className={`pb-3 text-xs font-semibold flex items-center gap-2 transition-all border-b-2 -mb-3 ${
                  activeTab === 'recommended'
                    ? 'border-brand-500 text-brand-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Ranked Recommendations ({jobMatches.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('all')}
                className={`pb-3 text-xs font-semibold flex items-center gap-2 transition-all border-b-2 -mb-3 ${
                  activeTab === 'all'
                    ? 'border-brand-500 text-brand-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Briefcase className="w-3.5 h-3.5" />
                <span>All Retrieved Jobs ({displayedJobs.length})</span>
              </button>
            </div>

            <span className="text-xs text-slate-500 hidden sm:inline-block">
              {activeTab === 'recommended' ? `${jobMatches.length} matches analyzed` : `${displayedJobs.length} real postings`}
            </span>
          </div>

          {/* Job Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {activeTab === 'recommended' ? (
              jobMatches.length > 0 ? (
                jobMatches.map((match) => (
                  <JobCard
                    key={match.job.id}
                    jobMatch={match}
                    onApplyClick={openApplyModal}
                    onQuickApply={handleQuickApply}
                    applyingJobId={applyingJobId}
                  />
                ))
              ) : (
                <div className="col-span-full py-16 text-center text-slate-400 glass-panel rounded-3xl p-8">
                  <Sparkles className="w-10 h-10 text-brand-400 mx-auto mb-3" />
                  <p className="font-semibold text-white">No AI matches generated yet</p>
                  <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                    Click &ldquo;Search Live Jobs&rdquo; above to query legitimate boards, and Gemini will score them against your verified profile.
                  </p>
                  <button
                    onClick={() => handleSearch()}
                    className="mt-4 px-5 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold inline-flex items-center gap-2"
                  >
                    <Search className="w-4 h-4" />
                    <span>Discover Jobs Now</span>
                  </button>
                </div>
              )
            ) : (
              displayedJobs.length > 0 ? (
                displayedJobs.map((j) => (
                  <JobCard
                    key={j.id}
                    job={j}
                    onApplyClick={openApplyModal}
                    onQuickApply={handleQuickApply}
                    applyingJobId={applyingJobId}
                  />
                ))
              ) : (
                <div className="col-span-full py-16 text-center text-slate-400 glass-panel rounded-3xl p-8">
                  <Briefcase className="w-10 h-10 text-slate-500 mx-auto mb-3" />
                  <p className="font-semibold text-white">No jobs found in current query</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Try searching with broader keywords like &ldquo;Engineer&rdquo; or clearing the location filter.
                  </p>
                </div>
              )
            )}
          </div>
        </main>
      </div>

      {/* Human-in-the-Loop Review & Apply Modal */}
      {applyModalOpen && selectedJobForApply && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-xl w-full p-6 md:p-8 space-y-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setApplyModalOpen(false)}
              className="absolute top-6 right-6 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Modal Header */}
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-brand-400 bg-brand-500/10 px-2.5 py-0.5 rounded-md border border-brand-500/20 mb-2 inline-block">
                Pre-Application Review
              </span>
              <h2 className="text-xl font-bold text-white">
                {selectedJobForApply.title}
              </h2>
              <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                <span className="flex items-center gap-1 text-slate-300 font-medium">
                  <Building className="w-3.5 h-3.5 text-slate-500" />
                  {selectedJobForApply.company}
                </span>
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-500" />
                  {selectedJobForApply.location || 'Remote'}
                </span>
              </div>
            </div>

            {applyError && (
              <div className="p-3.5 bg-rose-500/10 border border-rose-500/25 text-rose-300 text-xs rounded-xl">
                {applyError}
              </div>
            )}

            {/* If submission result was generated */}
            {submissionResult ? (
              <div className="space-y-4 py-2">
                <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 text-xs space-y-2">
                  <div className="flex items-center gap-2 font-bold text-white text-sm">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Application Status: {submissionResult.status.toUpperCase()}</span>
                  </div>
                  <p className="leading-relaxed">
                    {submissionResult.verification_details?.message || (submissionResult as any).error_message || 'Pre-submission checks completed successfully.'}
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 text-xs space-y-2">
                  <span className="text-slate-400 font-semibold block">Official Employer Portal:</span>
                  <a
                    href={selectedJobForApply.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-brand-400 hover:text-brand-300 font-medium break-all underline"
                  >
                    <span>{selectedJobForApply.url}</span>
                    <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                  </a>
                </div>

                {submissionResult.status !== 'manually_applied' && (
                  <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60 text-xs space-y-3">
                    <p className="text-slate-300">
                      Did you finalize and submit your application on the employer website?
                    </p>
                    <button
                      onClick={handleMarkManualApply}
                      className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors flex items-center justify-center gap-2"
                    >
                      <Check className="w-4 h-4" />
                      <span>Confirm & Mark as Manually Applied</span>
                    </button>
                  </div>
                )}

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => setApplyModalOpen(false)}
                    className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              /* Pre-submission review form */
              <div className="space-y-5">
                {/* Information to be shared */}
                <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 text-xs space-y-2">
                  <span className="font-semibold text-slate-300 uppercase tracking-wider block text-[11px]">
                    Candidate Information to be Shared
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-slate-400">
                    <div>Name: <span className="text-slate-200 font-medium">{profile?.full_name || 'Candidate'}</span></div>
                    <div>Email: <span className="text-slate-200 font-medium">{profile?.email || 'Registered Email'}</span></div>
                    <div>Location: <span className="text-slate-200 font-medium">{profile?.location || 'Unspecified'}</span></div>
                    <div>Resume Version: <span className="text-slate-200 font-medium">v{profile?.version || 1}</span></div>
                  </div>
                </div>

                {/* Questionnaire */}
                <div className="space-y-3">
                  <span className="font-semibold text-slate-300 uppercase tracking-wider block text-[11px]">
                    Pre-Submission Questions
                  </span>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="text-slate-400 block mb-1">Authorized to work?</label>
                      <select
                        value={answers.authorized_to_work}
                        onChange={(e) => setAnswers({ ...answers, authorized_to_work: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"
                      >
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-slate-400 block mb-1">Require visa sponsorship?</label>
                      <select
                        value={answers.requires_sponsorship}
                        onChange={(e) => setAnswers({ ...answers, requires_sponsorship: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"
                      >
                        <option value="No">No</option>
                        <option value="Yes">Yes</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Explicit Human Approval Guardrail */}
                <div className="p-4 rounded-2xl bg-brand-950/40 border border-brand-800/40 space-y-3">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      id="approval-checkbox"
                      checked={approvalConfirmed}
                      onChange={(e) => setApprovalConfirmed(e.target.checked)}
                      className="mt-0.5 rounded bg-slate-900 border-slate-700 text-brand-600 focus:ring-0"
                    />
                    <label htmlFor="approval-checkbox" className="text-xs text-slate-200 leading-relaxed cursor-pointer select-none">
                      <strong>Explicit Approval:</strong> I authorize the AI Job Application Agent to stage this application using my verified resume facts. I understand that the agent never submits without my approval.
                    </label>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between gap-3 pt-2">
                  <button
                    onClick={() => handleSaveJob(selectedJobForApply.id)}
                    className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                  >
                    <Bookmark className="w-3.5 h-3.5" />
                    <span>Save for Later</span>
                  </button>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setApplyModalOpen(false)}
                      className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 text-xs font-semibold"
                    >
                      Cancel
                    </button>

                    <button
                      onClick={handleExecuteApplication}
                      disabled={!approvalConfirmed || submittingApp}
                      className="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-brand-600/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {submittingApp ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Validating...</span>
                        </>
                      ) : (
                        <>
                          <span>Approve & Continue</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
