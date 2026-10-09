'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api } from '../lib/api';
import { Bot, LogOut, Sparkles } from 'lucide-react';

export default function Navbar({ userEmail }: { userEmail?: string }) {
  const router = useRouter();

  const handleLogout = () => {
    api.logout();
    router.push('/login');
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-lg text-white tracking-tight flex items-center gap-1.5">
              AI Job Agent
              <span className="text-[10px] uppercase font-semibold bg-brand-500/20 text-brand-400 px-1.5 py-0.5 rounded border border-brand-500/30">Gemini</span>
            </span>
          </div>
        </Link>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 bg-slate-800/60 px-3 py-1.5 rounded-full border border-slate-700/60">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Single Agent Architecture Active</span>
        </div>

        {userEmail && (
          <div className="flex items-center gap-3 pl-2 border-l border-slate-800">
            <div className="text-right hidden md:block">
              <p className="text-xs font-medium text-slate-200">{userEmail}</p>
              <p className="text-[11px] text-slate-400">Authenticated User</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 rounded-lg transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
