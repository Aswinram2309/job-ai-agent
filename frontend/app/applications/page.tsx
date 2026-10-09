'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../lib/api';
import { Application, ApplicationStatus } from '../../types';
import Navbar from '../../components/Navbar';
import Sidebar from '../../components/Sidebar';
import {
  Send, ExternalLink, CheckCircle2, Clock, AlertCircle,
  Building, MapPin, Calendar, FileText, Check, ShieldCheck,
  Search, Filter, ChevronRight, X, Loader2
} from 'lucide-react';

export default function ApplicationsPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [manualNote, setManualNote] = useState('');
  const [manualRefId, setManualRefId] = useState('');
  const [savingManual, setSavingManual] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchApps = async () => {
    try {
      const data = await api.getApplications();
      setApplications(data);
    } catch (err) {
      console.error('Failed to load applications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const token = api.getToken();
    if (!token) {
      router.replace('/login');
      return;
    }
    fetchApps();
  }, [router]);

  const handleManualApplySubmit = async (appId: string) => {
    setSavingManual(true);
    try {
      const updated = await api.manualApply(
        appId,
        manualNote || 'Applied directly on employer portal',
        manualRefId || `MANUAL-${Date.now()}`
      );
      setApplications(prev => prev.map(a => a.id === updated.id ? updated : a));
      setSelectedApp(updated);
    } catch (err) {
      console.error('Failed to mark manually applied:', err);
    } finally {
      setSavingManual(false);
    }
  };

  const getStatusBadge = (status: ApplicationStatus) => {
    switch (status) {
      case 'submitted':
      case 'verified':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Submitted</span>
          </span>
        );
      case 'manually_applied':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Check className="w-3.5 h-3.5" />
            <span>Manually Applied</span>
          </span>
        );
      case 'ready_to_apply':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Clock className="w-3.5 h-3.5" />
            <span>Ready to Apply</span>
          </span>
        );
      case 'saved':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <span>Saved</span>
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Submission Failed</span>
          </span>
        );
      case 'awaiting_approval':
      case 'needs_user_action':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5" />
            <span>Awaiting Action</span>
          </span>
        );
    }
  };

  const filteredApps = applications.filter(app => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'applied') return app.status === 'submitted' || app.status === 'verified' || app.status === 'manually_applied';
    if (statusFilter === 'ready') return app.status === 'ready_to_apply' || app.status === 'awaiting_approval';
    if (statusFilter === 'saved') return app.status === 'saved';
    return true;
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <Navbar />

      <div className="flex-1 flex">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full space-y-8">
          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/20 mb-2">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Truthful Audit Record
            </span>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Application History & Tracking
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Complete, truthful audit trail of all candidate-approved applications, verification references, and submissions.
            </p>
          </div>

          {/* Filter Bar */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  statusFilter === 'all'
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                All ({applications.length})
              </button>
              <button
                onClick={() => setStatusFilter('applied')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  statusFilter === 'applied'
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                Submitted / Applied
              </button>
              <button
                onClick={() => setStatusFilter('ready')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  statusFilter === 'ready'
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                Ready to Apply
              </button>
              <button
                onClick={() => setStatusFilter('saved')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  statusFilter === 'saved'
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                Saved
              </button>
            </div>
          </div>

          {/* Applications Listing */}
          {loading ? (
            <div className="p-16 flex justify-center items-center text-slate-400 gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
              <span className="text-sm">Loading applications history...</span>
            </div>
          ) : filteredApps.length > 0 ? (
            <div className="grid grid-cols-1 gap-4">
              {filteredApps.map((app) => (
                <div
                  key={app.id}
                  className="bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-3xl p-6 transition-all backdrop-blur-sm flex flex-col md:flex-row md:items-center justify-between gap-6"
                >
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-brand-400 bg-brand-500/10 px-2.5 py-0.5 rounded border border-brand-500/20">
                        {app.job?.provider || 'Official Portal'}
                      </span>
                      {getStatusBadge(app.status)}
                    </div>

                    <h3 className="text-base font-bold text-white">
                      {app.job?.title || 'Job Opening'}
                    </h3>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
                      <span className="flex items-center gap-1 text-slate-300 font-medium">
                        <Building className="w-3.5 h-3.5 text-slate-500" />
                        {app.job?.company || 'Company'}
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-500" />
                        {app.job?.location || 'Remote'}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        Created: {new Date(app.created_at).toLocaleDateString()}
                      </span>
                      {app.resume_version && (
                        <span className="flex items-center gap-1 bg-slate-800 px-2 py-0.5 rounded border border-slate-700 text-[11px]">
                          Resume v{app.resume_version}
                        </span>
                      )}
                    </div>

                    {app.submission_reference && (
                      <p className="text-xs text-emerald-400 font-mono">
                        Confirmation Reference: {app.submission_reference}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    {app.job?.url && (
                      <a
                        href={app.job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
                      >
                        <span>Official Portal</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}

                    <button
                      onClick={() => {
                        setSelectedApp(app);
                        setManualNote('');
                        setManualRefId(app.submission_reference || '');
                      }}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold transition-all shadow-md shadow-brand-600/20"
                    >
                      <span>Inspect Details</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-20 text-center text-slate-400 glass-panel rounded-3xl p-8">
              <Send className="w-10 h-10 text-slate-500 mx-auto mb-3" />
              <p className="font-semibold text-white">No applications matching this filter</p>
              <p className="text-xs text-slate-400 mt-1">
                Explore recommended job postings to review and submit genuine applications.
              </p>
            </div>
          )}
        </main>
      </div>

      {/* Details & Manual Confirmation Drawer / Modal */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 md:p-8 space-y-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setSelectedApp(null)}
              className="absolute top-6 right-6 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div>
              <div className="flex items-center gap-2 mb-2">
                {getStatusBadge(selectedApp.status)}
              </div>
              <h2 className="text-xl font-bold text-white">
                {selectedApp.job?.title || 'Application Details'}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {selectedApp.job?.company} • ID: {selectedApp.id.slice(0, 8)}...
              </p>
            </div>

            {/* Verification details */}
            <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 text-xs space-y-2">
              <span className="font-semibold text-slate-300 block uppercase tracking-wider text-[11px]">
                Submission Audit Data
              </span>
              <p className="text-slate-300 leading-relaxed">
                {selectedApp.verification_details?.message || 'Pre-submission validation completed.'}
              </p>
              {selectedApp.submission_reference && (
                <div className="pt-2 text-emerald-400 font-mono">
                  Receipt ID: {selectedApp.submission_reference}
                </div>
              )}
              {selectedApp.submitted_at && (
                <div className="text-slate-400">
                  Timestamp: {new Date(selectedApp.submitted_at).toLocaleString()}
                </div>
              )}
            </div>

            {/* Manual Confirmation section if not yet applied */}
            {selectedApp.status !== 'manually_applied' && selectedApp.status !== 'submitted' && (
              <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60 text-xs space-y-3">
                <span className="font-semibold text-white block">
                  Confirm Manual Submission
                </span>
                <p className="text-slate-300">
                  If you visited the official employer link and completed your application, confirm here to update your tracked status:
                </p>

                <div>
                  <label className="text-slate-400 block mb-1">Confirmation / Reference ID (Optional)</label>
                  <input
                    type="text"
                    value={manualRefId}
                    onChange={(e) => setManualRefId(e.target.value)}
                    placeholder="e.g. APPL-98210"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"
                  />
                </div>

                <div>
                  <label className="text-slate-400 block mb-1">Notes (Optional)</label>
                  <input
                    type="text"
                    value={manualNote}
                    onChange={(e) => setManualNote(e.target.value)}
                    placeholder="e.g. Completed online assessment"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"
                  />
                </div>

                <button
                  onClick={() => handleManualApplySubmit(selectedApp.id)}
                  disabled={savingManual}
                  className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors flex items-center justify-center gap-2"
                >
                  <Check className="w-4 h-4" />
                  <span>{savingManual ? 'Updating...' : 'Mark as Manually Applied'}</span>
                </button>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedApp(null)}
                className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
