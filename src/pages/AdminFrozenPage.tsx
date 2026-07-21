import { Link } from 'react-router-dom';

// The admin dashboard is frozen — predictions now show automatically
// from Bzzoiro's own data with no manual curation step needed. The real
// AdminDashboard component (and all match_stats data) is untouched and
// still importable at any time if manual curation is ever needed again
// — this route just doesn't render it anymore.
export default function AdminFrozenPage() {
  return (
    <div className="pt-32 pb-16 min-h-screen flex items-center justify-center">
      <div className="max-w-md mx-auto px-4 text-center">
        <div className="text-5xl mb-4">🧊</div>
        <h1 className="text-2xl font-bold text-white mb-3">Admin Dashboard Frozen</h1>
        <p className="text-slate-400 mb-8">
          Manual curation is no longer needed — predictions with real Bzzoiro data now appear on the
          homepage automatically.
        </p>
        <Link
          to="/"
          className="inline-block px-6 py-3 rounded-full bg-brand-green hover:bg-brand-green-hover text-white font-bold transition-colors"
        >
          ← Back to Home
        </Link>
      </div>
    </div>
  );
}
