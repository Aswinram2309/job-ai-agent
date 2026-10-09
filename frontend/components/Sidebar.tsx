'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, FileText, Briefcase, Send, Settings, Sparkles } from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Resume & Profile', href: '/resume', icon: FileText },
  { label: 'Job Matches', href: '/jobs', icon: Briefcase },
  { label: 'Applications', href: '/applications', icon: Send },
  { label: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/40 p-4 flex flex-col justify-between hidden md:flex shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold uppercase text-slate-500 tracking-wider">
          Navigation
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 shadow-sm shadow-brand-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-brand-400' : 'text-slate-500'}`} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>

      <div className="p-4 rounded-2xl bg-gradient-to-b from-slate-800/60 to-slate-800/30 border border-slate-700/50">
        <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-amber-400">
          <Sparkles className="w-4 h-4" />
          <span>Safety Safeguard</span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          The agent never submits job applications without your explicit review and confirmation.
        </p>
      </div>
    </aside>
  );
}
