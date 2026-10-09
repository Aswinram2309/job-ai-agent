'use client';

import React, { useState } from 'react';
import { CandidateProfile as ProfileType } from '../types';
import { api } from '../lib/api';
import {
  User, Briefcase, GraduationCap, Code2, Award,
  MapPin, AlertTriangle, Check, Edit3, Save, X
} from 'lucide-react';

interface CandidateProfileProps {
  profile: ProfileType;
  onProfileUpdated: (updated: ProfileType) => void;
}

export default function CandidateProfileView({ profile, onProfileUpdated }: CandidateProfileProps) {
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<ProfileType>>({ ...profile });
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await api.updateProfile(formData);
      onProfileUpdated(updated);
      setEditing(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 md:p-8 backdrop-blur-sm space-y-8">
      {/* Header with edit button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <User className="w-5 h-5 text-brand-400" />
            Candidate Profile
            <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">
              v{profile.version}
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Verified candidate facts extracted from your resume.
          </p>
        </div>

        <div>
          {!editing ? (
            <button
              onClick={() => setEditing(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
            >
              <Edit3 className="w-3.5 h-3.5 text-brand-400" />
              <span>Edit Profile Details</span>
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setFormData({ ...profile });
                  setEditing(false);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-400 border border-slate-700 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white transition-colors"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{saving ? 'Saving...' : 'Save Changes'}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {saveSuccess && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 rounded-xl text-xs flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>Profile changes saved and updated across all job matching workflows.</span>
        </div>
      )}

      {saveError && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-xl text-xs">
          {saveError}
        </div>
      )}

      {/* Basic Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800">
          <span className="text-xs text-slate-400 block mb-1">Full Name</span>
          {editing ? (
            <input
              type="text"
              value={formData.full_name || ''}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-sm text-white"
            />
          ) : (
            <span className="text-sm font-semibold text-white">{profile.full_name || 'Not specified'}</span>
          )}
        </div>

        <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800">
          <span className="text-xs text-slate-400 block mb-1">Email Address</span>
          {editing ? (
            <input
              type="email"
              value={formData.email || ''}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-sm text-white"
            />
          ) : (
            <span className="text-sm font-semibold text-white">{profile.email || 'Not specified'}</span>
          )}
        </div>

        <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800">
          <span className="text-xs text-slate-400 block mb-1">Location</span>
          {editing ? (
            <input
              type="text"
              value={formData.location || ''}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-sm text-white"
            />
          ) : (
            <span className="text-sm font-semibold text-white flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-rose-400" />
              {profile.location || 'Not specified'}
            </span>
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="p-5 rounded-2xl bg-slate-800/30 border border-slate-800">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Professional Summary</span>
        {editing ? (
          <textarea
            rows={3}
            value={formData.summary || ''}
            onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-white"
          />
        ) : (
          <p className="text-sm text-slate-300 leading-relaxed">{profile.summary || 'No summary extracted from resume.'}</p>
        )}
      </div>

      {/* Technical & Soft Skills */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-5 rounded-2xl bg-slate-800/30 border border-slate-800">
          <div className="flex items-center gap-2 mb-3">
            <Code2 className="w-4 h-4 text-brand-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Technical Skills</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {profile.technical_skills && profile.technical_skills.length > 0 ? (
              profile.technical_skills.map((skill, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-medium"
                >
                  {skill}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">None detected</span>
            )}
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-800/30 border border-slate-800">
          <div className="flex items-center gap-2 mb-3">
            <Award className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Soft Skills</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {profile.soft_skills && profile.soft_skills.length > 0 ? (
              profile.soft_skills.map((skill, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-medium"
                >
                  {skill}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">None detected</span>
            )}
          </div>
        </div>
      </div>

      {/* Work Experience */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Briefcase className="w-4 h-4 text-brand-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Work Experience</h3>
        </div>
        <div className="space-y-3">
          {profile.work_experience && profile.work_experience.length > 0 ? (
            profile.work_experience.map((exp, i) => (
              <div key={i} className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-semibold text-white text-sm">{exp.title}</h4>
                    <span className="text-xs text-brand-300 font-medium">{exp.company}</span>
                  </div>
                  {exp.duration && (
                    <span className="text-xs text-slate-400 bg-slate-800 px-2.5 py-0.5 rounded-full border border-slate-700">
                      {exp.duration}
                    </span>
                  )}
                </div>
                {exp.responsibilities && exp.responsibilities.length > 0 && (
                  <ul className="mt-2 list-disc list-inside text-xs text-slate-300 space-y-1">
                    {exp.responsibilities.map((r, idx) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500 italic">No previous employment entries recorded.</p>
          )}
        </div>
      </div>

      {/* Education */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <GraduationCap className="w-4 h-4 text-brand-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Education</h3>
        </div>
        <div className="space-y-3">
          {profile.education && profile.education.length > 0 ? (
            profile.education.map((edu, i) => (
              <div key={i} className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 flex justify-between items-center">
                <div>
                  <h4 className="font-semibold text-white text-sm">{edu.degree}</h4>
                  <span className="text-xs text-slate-400">{edu.institution}</span>
                </div>
                {edu.graduation_year && (
                  <span className="text-xs text-slate-400 bg-slate-800 px-2.5 py-0.5 rounded-full border border-slate-700">
                    {edu.graduation_year}
                  </span>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500 italic">No formal education entries recorded.</p>
          )}
        </div>
      </div>

      {/* Missing or Uncertain Information (Transparency Guarantee) */}
      {profile.missing_information && profile.missing_information.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20">
          <div className="flex items-center gap-2 mb-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
            <AlertTriangle className="w-4 h-4" />
            <span>Missing or Uncertain Information Detected by Gemini</span>
          </div>
          <ul className="list-disc list-inside text-xs text-amber-200/90 space-y-1">
            {profile.missing_information.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
