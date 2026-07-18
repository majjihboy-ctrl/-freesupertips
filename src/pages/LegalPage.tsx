import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

export default function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="pt-24 pb-16 min-h-screen">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <Link to="/" className="text-brand-green hover:underline mb-6 inline-block">
          ← Back to Home
        </Link>
        <h1 className="text-3xl sm:text-4xl font-bold text-white mb-8">{title}</h1>
        <div className="prose prose-invert prose-slate max-w-none text-slate-300 leading-relaxed space-y-4 [&_h2]:text-white [&_h2]:font-bold [&_h2]:text-xl [&_h2]:mt-8 [&_h2]:mb-3">
          {children}
        </div>
      </div>
    </div>
  );
}
