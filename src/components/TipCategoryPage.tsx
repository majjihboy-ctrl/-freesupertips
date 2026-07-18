import { useParams, Link } from 'react-router-dom';
import DailyPredictions from './DailyPredictions';

// Only these are actually derivable from a manually-entered tip's text
// (home/away/draw win, over 2.5, BTTS). Any other category slug gets an
// honest "not available yet" message instead of silently showing the
// full unfiltered list under a misleading heading.
const CATEGORY_FILTERS: Record<string, { filterPrediction: string }> = {
  'home-win': { filterPrediction: 'Win' },
  'away-win': { filterPrediction: 'Win' },
  draws: { filterPrediction: 'Draw' },
  'over-2.5': { filterPrediction: 'Over 2.5' },
  'btts/gg': { filterPrediction: 'Both Teams' },
};

export default function TipCategoryPage() {
  const { category } = useParams();
  const key = (category || '').toLowerCase();
  const config = CATEGORY_FILTERS[key];
  const displayName = (category || '').replace(/-/g, ' ').toUpperCase();

  return (
    <div className="pt-24 pb-16 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <Link to="/" className="text-brand-green hover:underline mb-4 inline-block">← Back to Home</Link>
          <h1 className="text-4xl font-bold text-white mb-2">{displayName} Tips</h1>
          <p className="text-slate-400">Specialized predictions for {displayName.toLowerCase()}</p>
        </div>

        {config ? (
          <DailyPredictions filterPrediction={config.filterPrediction} />
        ) : (
          <div className="text-center py-16 text-slate-400 bg-bg-surface rounded-2xl border border-bg-surface-hover">
            This tip category isn't available yet — check back soon, or see{' '}
            <Link to="/" className="text-brand-green hover:underline">all today's tips</Link>.
          </div>
        )}
      </div>
    </div>
  );
}
