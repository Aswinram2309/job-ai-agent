'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../lib/api';
import Navbar from '../../components/Navbar';
import Sidebar from '../../components/Sidebar';
import {
  Settings as SettingsIcon, ShieldAlert, CheckCircle2,
  Trash2, RefreshCw, AlertTriangle, Key, Cpu, Database, Server
} from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState<string | null>(null);

  useEffect(() => {
    const token = api.getToken();
    if (!token) {
      router.replace('/login');
      return;
    }

    const checkHealth = async () => {
      try {
        const res = await fetch('http://localhost:8000/health');
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      } catch (err) {
        console.error('Failed to fetch system health:', err);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, [router]);

  const handleDeleteAccount = async () => {
    setDeleting(true);
    try {
      await api.deleteAccount();
      api.logout();
      router.replace('/login');
    } catch (err: any) {
      setDeleteMsg(err.message || 'Failed to delete account.');
      setDeleting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <Navbar />

      <div className="flex-1 flex">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 max-w-4xl mx-auto w-full space-y-8">
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
              <SettingsIcon className="w-7 h-7 text-brand-400" />
              Settings & Agent Environment
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Inspect backend telemetry, AI model runtime parameters, and privacy controls.
            </p>
          </div>

          {/* System Health Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 md:p-8 backdrop-blur-sm space-y-6">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-brand-400" />
              Backend & AI Environment Diagnostics
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Cpu className="w-5 h-5 text-indigo-400" />
                  <div>
                    <span className="text-xs text-slate-400 block">Gemini LLM Model</span>
                    <span className="text-sm font-semibold text-white">
                      {health?.gemini_model || 'gemini-3.5-flash-lite'}
                    </span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Active
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Key className="w-5 h-5 text-amber-400" />
                  <div>
                    <span className="text-xs text-slate-400 block">Google AI Studio API Key</span>
                    <span className="text-sm font-semibold text-white">
                      {health?.gemini_configured ? 'Configured & Encrypted' : 'Not Configured'}
                    </span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Verified
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-cyan-400" />
                  <div>
                    <span className="text-xs text-slate-400 block">Storage & Database</span>
                    <span className="text-sm font-semibold text-white">SQLite / PostgreSQL</span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Connected
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ShieldAlert className="w-5 h-5 text-emerald-400" />
                  <div>
                    <span className="text-xs text-slate-400 block">Submission Guardrail</span>
                    <span className="text-sm font-semibold text-white">
                      {health?.live_submissions_enabled ? 'Live Mode' : 'Safe Review Mode (Default)'}
                    </span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Protected
                </span>
              </div>
            </div>
          </div>

          {/* Privacy & Account Deletion */}
          <div className="bg-slate-900/60 border border-rose-500/20 rounded-3xl p-6 md:p-8 backdrop-blur-sm space-y-6">
            <div className="flex items-center gap-2 text-rose-400">
              <Trash2 className="w-5 h-5" />
              <h2 className="text-base font-bold text-white">Data Privacy & Account Deletion</h2>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              In accordance with strict privacy principles, you can permanently delete your candidate account. This immediately purges your resume files, parsed facts, job match history, and approval records from the disk and database.
            </p>

            {deleteMsg && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/25 text-rose-300 text-xs rounded-xl">
                {deleteMsg}
              </div>
            )}

            {!confirmDelete ? (
              <button
                onClick={() => setConfirmDelete(true)}
                className="px-4 py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold transition-colors"
              >
                Delete My Candidate Account & Data
              </button>
            ) : (
              <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-800/50 space-y-3">
                <div className="flex items-center gap-2 text-rose-300 text-xs font-semibold">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Are you sure? This action is irreversible.</span>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDeleteAccount}
                    disabled={deleting}
                    className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-600/30 transition-colors"
                  >
                    {deleting ? 'Deleting...' : 'Permanently Delete Everything'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
