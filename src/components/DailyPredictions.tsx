import { useState, useEffect } from 'react';
import { Calendar, Crown, Loader2, Lock } from 'lucide-react';
import { fetchUpcomingFixtures, type Fixture } from '../api/football';
import { useAuth } from '../hooks/useAuth';
import { usePremium } from '../hooks/usePremium';

interface DailyPredictionsProps {
  filterPrediction?: string; // substring match against match.prediction, e.g. "Over 2.5"
}

export default function DailyPredictions({ filterPrediction }: DailyPredictionsProps) {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const { hasPremium } = usePremium(user?.id ?? null);
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchUpcomingFixtures().then((data) => {
      if (!cancelled) {
        setFixtures(data);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const displayFixtures = filterPrediction
    ? fixtures.filter((f) => f.prediction.toLowerCase().includes(filterPrediction.toLowerCase()))
    : fixtures;

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 bg-bg-surface">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3">Today's Football Predictions</h2>
          <p className="text-slate-400 flex items-center justify-center gap-2 text-lg">
            <Calendar className="w-5 h-5 text-brand-green" />
            {today}
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-4 mb-10">
          <a
            href="/pricing"
            className="px-8 py-3.5 bg-brand-green text-white rounded-full font-bold hover:bg-brand-green-hover transition-all shadow-lg flex items-center gap-2 hover:-translate-y-0.5"
          >
            <Crown className="w-5 h-5" />
            JOIN VIP TIPS
          </a>
        </div>

        <div className="overflow-x-auto rounded-2xl shadow-xl border border-bg-surface-hover bg-bg-surface">
          <table className="w-full text-left">
            <thead className="bg-bg-base text-white">
              <tr>
                <th className="px-6 py-5 font-bold text-sm uppercase tracking-wider">League / Game</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Tip</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bg-surface-hover">
              {loading ? (
                <tr>
                  <td colSpan={2} className="px-6 py-16 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading today's predictions…
                  </td>
                </tr>
              ) : displayFixtures.length === 0 ? (
                <tr>
                  <td colSpan={2} className="px-6 py-16 text-center text-slate-400">
                    No predictions posted yet. Check back soon.
                  </td>
                </tr>
              ) : (
                displayFixtures.map((match, index) => {
                  const locked = match.isPremium && !hasPremium;
                  return (
                    <tr key={match.id} className={index % 2 === 0 ? 'bg-bg-surface' : 'bg-bg-base/40'}>
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 bg-bg-base rounded-full flex items-center justify-center text-xl">⚽</div>
                          <div>
                            <div className="text-sm text-slate-400 font-medium">
                              {match.league} • {match.time}
                            </div>
                            <div className="font-bold text-white text-base mt-0.5">
                              {match.homeTeam} vs {match.awayTeam}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5 text-center">
                        {locked ? (
                          <a
                            href="/pricing"
                            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full font-bold text-sm shadow-sm bg-gradient-to-r from-yellow-400 to-orange-500 text-white"
                          >
                            <Lock className="w-3.5 h-3.5" /> VIP Only
                          </a>
                        ) : (
                          <span className="inline-block px-4 py-2 rounded-full font-bold text-sm shadow-sm bg-brand-green text-white">
                            {match.prediction}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
