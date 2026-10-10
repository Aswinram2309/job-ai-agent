'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '../lib/api';
import { Loader2 } from 'lucide-react';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = api.getToken();
    const dest = token ? '/dashboard' : '/login';
    router.replace(dest);

    // Fallback safety timeout if Next.js client router is slow
    const timer = setTimeout(() => {
      window.location.href = dest;
    }, 400);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center bg-slate-950">
      <div className="flex flex-col items-center gap-3 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
        <p className="text-sm">Loading AI Job Application Agent...</p>
        <div className="flex items-center gap-4 mt-2 text-xs">
          <Link href="/dashboard" className="text-brand-400 hover:text-brand-300 underline font-medium">
            Open Dashboard →
          </Link>
          <Link href="/login" className="text-slate-400 hover:text-slate-200 underline font-medium">
            Open Login →
          </Link>
        </div>
      </div>
    </div>
  );
}
