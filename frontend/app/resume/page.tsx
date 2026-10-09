'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../lib/api';
import { CandidateProfile } from '../../types';
import Navbar from '../../components/Navbar';
import Sidebar from '../../components/Sidebar';
import ResumeUploader from '../../components/ResumeUploader';
import CandidateProfileView from '../../components/CandidateProfile';
import { FileText, Loader2, Sparkles, CheckCircle2 } from 'lucide-react';

export default function ResumePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploadSuccessAlert, setUploadSuccessAlert] = useState<string | null>(null);

  const fetchProfile = async () => {
    try {
      const data = await api.getProfile();
      setProfile(data);
    } catch (err) {
      console.error('Failed to load candidate profile:', err);
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
    fetchProfile();
  }, [router]);

  const handleUploadSuccess = (analysisResult: any) => {
    setUploadSuccessAlert(`Resume '${analysisResult.filename}' processed successfully! Candidate facts extracted.`);
    fetchProfile();
    setTimeout(() => setUploadSuccessAlert(null), 5000);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <Navbar userEmail={profile?.email} />

      <div className="flex-1 flex">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 max-w-5xl mx-auto w-full space-y-8">
          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/20 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-brand-400" />
              Verified Candidate Profile
            </span>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Resume & Truthful Profile
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Upload your genuine resume. Gemini extracts your validated credentials, and you maintain complete control to edit and review before job matching.
            </p>
          </div>

          {uploadSuccessAlert && (
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-sm flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <span>{uploadSuccessAlert}</span>
            </div>
          )}

          {/* Resume Upload Module */}
          <ResumeUploader onUploadSuccess={handleUploadSuccess} />

          {/* Profile Details or Loading */}
          {loading ? (
            <div className="p-12 flex justify-center items-center text-slate-400 gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
              <span className="text-sm">Loading candidate profile...</span>
            </div>
          ) : profile ? (
            <CandidateProfileView
              profile={profile}
              onProfileUpdated={(updated) => setProfile(updated)}
            />
          ) : null}
        </main>
      </div>
    </div>
  );
}
