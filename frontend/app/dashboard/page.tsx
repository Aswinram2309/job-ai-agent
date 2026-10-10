'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '../../lib/api';
import { DashboardStats, CandidateProfile, AgentToolCallInfo } from '../../types';
import Navbar from '../../components/Navbar';
import Sidebar from '../../components/Sidebar';
import {
  FileText, Briefcase, Send, CheckCircle2, AlertCircle,
  ArrowRight, Sparkles, Bot, Loader2, RefreshCw, BookmarkCheck
} from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string>('');

  // AI Agent Chat state
  const [chatMessage, setChatMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string; tools?: AgentToolCallInfo[] }[]>([
    {
      role: 'model',
      content: 'Hello! I am your AI Job Application Agent powered by Google Gemini. I can search real job openings, analyze your resume alignment, evaluate missing skills, and stage user-approved applications. How can I help you today?'
    }
  ]);

  const loadData = async () => {
    try {
      const [statsData, profileData] = await Promise.all([
        api.getDashboardStats(),
        api.getProfile().catch(() => null)
      ]);
      setStats(statsData);
      setProfile(profileData);
      if (profileData?.email) {
        setUserEmail(profileData.email);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
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
    loadData();
  }, [router]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim() || chatLoading) return;

    const userText = chatMessage.trim();
    setChatMessage('');
    setChatHistory(prev => [...prev, { role: 'user', content: userText }]);
    setChatLoading(true);

    try {
      const formattedHistory = chatHistory.map(h => ({ role: h.role, content: h.content }));
      const response = await api.chatWithAgent(userText, formattedHistory);
      setChatHistory(prev => [
        ...prev,
        { role: 'model', content: response.reply, tools: response.tools_executed }
      ]);
      // Refresh dashboard stats in case agent executed tools like search or approve
      if (response.tools_executed && response.tools_executed.length > 0) {
        loadData();
      }
    } catch (err: any) {
      setChatHistory(prev => [
        ...prev,
        { role: 'model', content: `Error: ${err.message || 'Failed to communicate with AI agent.'}` }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case 'verified':
      case 'submitted':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Submitted</span>;
      case 'manually_applied':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">Manually Applied</span>;
      case 'ready_to_apply':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Ready to Apply</span>;
      case 'saved':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">Saved</span>;
      case 'awaiting_approval':
      case 'needs_user_action':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Action Required</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">{statusStr}</span>;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <Navbar userEmail={userEmail} />

      <div className="flex-1 flex">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full space-y-8">
          {/* Welcome Banner */}
          <div className="bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-800/80 border border-slate-800 rounded-3xl p-6 md:p-8 backdrop-blur-sm relative overflow-hidden shadow-xl">
            <div className="absolute right-0 top-0 w-80 h-80 bg-brand-600/10 rounded-full blur-3xl pointer-events-none" />
            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/20 mb-3">
                  <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                  Production Ready Agent
                </span>
                <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
                  Welcome back, {profile?.full_name || 'Candidate'}
                </h1>
                <p className="text-sm text-slate-400 mt-1 max-w-xl">
                  Your AI Agent operates with strict truthfulness: real job postings from official sources, transparent match scoring, and zero unauthorized submissions.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href="/resume"
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all"
                >
                  <FileText className="w-4 h-4 text-brand-400" />
                  <span>Resume & Profile</span>
                </Link>
                <Link
                  href="/jobs"
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-lg shadow-brand-600/25 transition-all"
                >
                  <Briefcase className="w-4 h-4" />
                  <span>Explore Jobs</span>
                </Link>
              </div>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Resume Status</span>
              <p className="text-sm font-bold text-white mt-1 flex items-center gap-1.5">
                {stats?.has_resume ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Active</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                    <span className="text-amber-300">Upload Needed</span>
                  </>
                )}
              </p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Skills Detected</span>
              <p className="text-xl font-extrabold text-white mt-1">{stats?.skills_detected || 0}</p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Real Jobs Synced</span>
              <p className="text-xl font-extrabold text-white mt-1">{stats?.total_jobs_found || 0}</p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">AI Matches</span>
              <p className="text-xl font-extrabold text-brand-400 mt-1">{stats?.recommended_jobs || 0}</p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Saved Roles</span>
              <p className="text-xl font-extrabold text-purple-400 mt-1">{stats?.saved_jobs || 0}</p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Applications</span>
              <p className="text-xl font-extrabold text-emerald-400 mt-1">{stats?.applications_submitted || 0}</p>
            </div>
          </div>

          {/* Two-Column: Interactive Agent Chat & Recent Applications */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Interactive Agent Chat */}
            <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 flex flex-col justify-between backdrop-blur-sm shadow-xl min-h-[500px]">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-brand-600/20 border border-brand-500/30 flex items-center justify-center text-brand-400">
                      <Bot className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white text-sm">Gemini Autonomous Assistant</h3>
                      <p className="text-[11px] text-slate-400">Equipped with real Python search and matching tools</p>
                    </div>
                  </div>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">
                    Live Session
                  </span>
                </div>

                {/* Messages scroll box */}
                <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2">
                  {chatHistory.map((item, idx) => (
                    <div
                      key={idx}
                      className={`flex flex-col ${item.role === 'user' ? 'items-end' : 'items-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                          item.role === 'user'
                            ? 'bg-brand-600 text-white rounded-br-xs'
                            : 'bg-slate-800/70 border border-slate-700/60 text-slate-200 rounded-bl-xs'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{item.content}</p>
                        {item.tools && item.tools.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-slate-700 text-[10px] text-brand-300">
                            <span className="font-semibold block mb-1">Executed Tools:</span>
                            {item.tools.map((t, tidx) => (
                              <span key={tidx} className="inline-block bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800 mr-1 mb-1">
                                {t.tool_name}()
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="flex items-center gap-2 text-xs text-brand-400 italic">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Gemini is evaluating and invoking tools...</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Chat Input form */}
              <form onSubmit={handleSendMessage} className="mt-4 pt-3 border-t border-slate-800 flex gap-2">
                <input
                  type="text"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  placeholder="e.g. Find remote Python engineer jobs or check alignment..."
                  className="flex-1 bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
                />
                <button
                  type="submit"
                  disabled={chatLoading || !chatMessage.trim()}
                  className="px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Send</span>
                </button>
              </form>
            </div>

            {/* Recent Applications Column */}
            <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 backdrop-blur-sm shadow-xl flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
                  <h3 className="font-bold text-white text-sm flex items-center gap-2">
                    <Send className="w-4 h-4 text-emerald-400" />
                    Application Pipeline
                  </h3>
                  <Link href="/applications" className="text-xs text-brand-400 hover:text-brand-300 font-medium">
                    View All
                  </Link>
                </div>

                <div className="space-y-3">
                  {stats?.recent_applications && stats.recent_applications.length > 0 ? (
                    stats.recent_applications.map((app) => (
                      <div
                        key={app.id}
                        className="p-3.5 rounded-2xl bg-slate-800/40 border border-slate-800 flex items-center justify-between gap-3"
                      >
                        <div>
                          <h4 className="text-xs font-semibold text-white">{app.job_title}</h4>
                          <span className="text-[11px] text-slate-400">{app.company}</span>
                        </div>
                        <div>
                          {getStatusBadge(app.status)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-10 text-slate-500 text-xs">
                      <p>No applications staged yet.</p>
                      <Link href="/jobs" className="text-brand-400 hover:underline mt-2 inline-block">
                        Browse recommended jobs →
                      </Link>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
                <span>Safe Mode Active</span>
                <span className="text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  User Consent Enforced
                </span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
