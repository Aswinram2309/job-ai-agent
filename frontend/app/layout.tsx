import './globals.css';
import type { Metadata } from 'next';
import React from 'react';

export const metadata: Metadata = {
  title: 'AI Job Application Agent | Powered by Google Gemini',
  description: 'Intelligent, truthful job search and application orchestration powered by Google Gemini LLM.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-brand-500/30 selection:text-brand-200">
        <div className="min-h-screen flex flex-col bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))]">
          {children}
        </div>
      </body>
    </html>
  );
}
