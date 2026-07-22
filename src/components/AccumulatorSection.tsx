import { useState, useEffect } from 'react';
import { Layers, Lock, Loader2 } from 'lucide-react';
import { fetchAccumulators, type Accumulator } from '../api/football';
import { useAuth } from '../hooks/useAuth';
import { usePremium } from '../hooks/usePremium';

export default function AccumulatorSection() {
  const [accumulators, setAccumulators] = useState<Accumulator[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const { hasPremium } = usePremium(user?.id ?? null);

  useEffect(() => {
    let cancelled = false;
    fetchAccumulators().then((data) => {
      if (!cancelled) {
        setAccumulators(data);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-bg-base">
        <div className="max-w-4xl mx-auto text-center text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
          Loading accumulators…
        </div>
      </section>
    );
  }

  if (accumulators.length === 0) return null; // nothing curated yet — don't show an empty section

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 bg-bg-base">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3 flex items-center justify-center gap-3">
            <Layers className="w-8 h-8 text-brand-green" />
            Accumulators
          </h2>
          <p className="text-slate-400">Hand-picked combinations from today's board</p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          {accumulators.map((acc) => {
            const locked = acc.isPremium && !hasPremium;
            return (
              <div key={acc.id} className="bg-bg-surface rounded-2xl border border-bg-surface-hover p-6 shadow-xl">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-white text-lg">{acc.title}</h3>
                  {acc.isPremium && (
                    <span className="text-xs font-bold text-brand-premium bg-brand-premium/10 px-2.5 py-1 rounded-full">VIP</span>
                  )}
                </div>

                {locked ? (
                  <a
                    href="/pricing"
                    className="flex flex-col items-center justify-center gap-2 py-8 text-brand-premium hover:text-yellow-400 transition-colors"
                  >
                    <Lock className="w-6 h-6" />
                    <span className="font-bold text-sm">Unlock this accumulator with VIP</span>
                  </a>
                ) : (
                  <ul className="space-y-3">
                    {acc.picks.map((pick) => (
                      <li key={pick.id} className="flex items-center justify-between text-sm border-b border-bg-surface-hover last:border-0 pb-3 last:pb-0">
                        <div>
                          <div className="text-white font-semibold">
                            {pick.homeTeam} vs {pick.awayTeam}
                          </div>
                          <div className="text-slate-500 text-xs">{pick.league}</div>
                        </div>
                        <span className="text-brand-green font-bold whitespace-nowrap ml-3">{pick.prediction}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
