import { type Fixture } from '../api/football';

interface AccumulatorSectionProps {
  predictions: Fixture[];
  hasPremium: boolean;
  onUpgradeClick: () => void;
}

export default function AccumulatorSection({ predictions, hasPremium, onUpgradeClick }: AccumulatorSectionProps) {
  // Ensure we have data to work with
  const availableMatches = predictions.length > 0 ? predictions : [];

  // 🧠 THE ALGORITHM: Dynamically pick the best from today's real fixtures

  // 1. SAFE ACCA: Top 3 matches with the absolute highest confidence
  const safeAcca = [...availableMatches]
    .sort((a, b) => parseInt(b.confidence.replace('%', '')) - parseInt(a.confidence.replace('%', '')))
    .slice(0, 3);

  // 2. HIGH ODDS ACCA: Top 3 matches with the highest odds
  const highOddsAcca = [...availableMatches]
    .sort((a, b) => parseFloat(b.odds) - parseFloat(a.odds))
    .slice(0, 3);

  // 3. VIP ACCA: Top 3 Premium matches with highest confidence.
  // (Fallback: If you haven't added Premium tips yet, it uses the highest confidence overall)
  const premiumMatches = availableMatches.filter(p => p.isPremium);
  const vipAcca = (premiumMatches.length >= 3 ? premiumMatches : availableMatches)
    .sort((a, b) => parseInt(b.confidence.replace('%', '')) - parseInt(a.confidence.replace('%', '')))
    .slice(0, 3);

  // Helper to calculate combined accumulator odds
  const calcCombinedOdds = (acca: Fixture[]) => {
    if (acca.length === 0) return "0.00";
    return acca.reduce((acc, curr) => acc * parseFloat(curr.odds), 1).toFixed(2);
  };

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          🤖 Auto-Generated Accumulators
        </h2>
        <span className="text-xs font-medium text-slate-400 bg-bg-surface px-3 py-1 rounded-full border border-bg-surface-hover">
          Based on today's {availableMatches.length} fixtures
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        {/* 1. SAFE ACCA */}
        <AccaCard
          title="Safe Acca"
          subtitle="Highest Confidence Picks"
          icon="🛡️"
          matches={safeAcca}
          combinedOdds={calcCombinedOdds(safeAcca)}
          colorClass="border-blue-500/30 bg-blue-500/5"
          textColor="text-blue-400"
        />

        {/* 2. HIGH ODDS ACCA */}
        <AccaCard
          title="High Odds Acca"
          subtitle="Massive Payout Potential"
          icon="🚀"
          matches={highOddsAcca}
          combinedOdds={calcCombinedOdds(highOddsAcca)}
          colorClass="border-orange-500/30 bg-orange-500/5"
          textColor="text-orange-400"
        />

        {/* 3. VIP ACCA */}
        <div className={`relative rounded-xl border-2 p-5 transition-all ${hasPremium ? 'border-brand-premium/50 bg-brand-premium/5' : 'border-brand-premium/20 bg-bg-surface'}`}>
          {!hasPremium && (
            <div className="absolute inset-0 bg-bg-base/80 backdrop-blur-md rounded-xl flex flex-col items-center justify-center z-10 p-4 text-center">
              <span className="text-4xl mb-2">🔒</span>
              <h4 className="text-lg font-bold text-white mb-2">VIP Acca Locked</h4>
              <p className="text-slate-400 text-sm mb-4">Unlock our highest confidence premium tips.</p>
              <button onClick={onUpgradeClick} className="bg-brand-premium hover:bg-brand-premium/80 text-white px-6 py-2 rounded-lg text-sm font-bold transition-colors">
                Unlock Premium
              </button>
            </div>
          )}
          <div className={hasPremium ? '' : 'opacity-30 blur-[2px]'}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">👑</span>
              <h3 className="text-lg font-bold text-white">VIP Acca</h3>
            </div>
            <p className="text-xs text-slate-400 mb-4">The Golden Picks of the Day</p>

            <div className="bg-bg-base/50 rounded-lg p-3 mb-4 flex justify-between items-center border border-brand-premium/20">
              <span className="text-xs font-bold text-slate-400 uppercase">Combined Odds</span>
              <span className="text-2xl font-black text-brand-premium">{calcCombinedOdds(vipAcca)}</span>
            </div>

            <div className="space-y-3">
              {vipAcca.map((m, i) => (
                <div key={i} className="flex justify-between items-start text-sm">
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-semibold truncate">{m.homeTeam} vs {m.awayTeam}</p>
                    <p className="text-brand-green text-xs font-bold">{m.prediction}</p>
                  </div>
                  <span className="text-slate-400 font-bold ml-2">{m.odds}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

// Reusable Card Component for Safe and High Odds
function AccaCard({ title, subtitle, icon, matches, combinedOdds, colorClass, textColor }: any) {
  return (
    <div className={`rounded-xl border p-5 ${colorClass} flex flex-col`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-2xl">{icon}</span>
        <h3 className="text-lg font-bold text-white">{title}</h3>
      </div>
      <p className="text-xs text-slate-400 mb-4">{subtitle}</p>

      <div className="bg-bg-base/50 rounded-lg p-3 mb-4 flex justify-between items-center border border-bg-surface-hover">
        <span className="text-xs font-bold text-slate-400 uppercase">Combined Odds</span>
        <span className={`text-2xl font-black ${textColor}`}>{combinedOdds}</span>
      </div>

      <div className="space-y-3 flex-1">
        {matches.map((m: Fixture, i: number) => (
          <div key={i} className="flex justify-between items-start text-sm">
            <div className="flex-1 min-w-0">
              <p className="text-white font-semibold truncate">{m.homeTeam} vs {m.awayTeam}</p>
              <p className="text-brand-green text-xs font-bold">{m.prediction}</p>
            </div>
            <span className="text-slate-400 font-bold ml-2">{m.odds}</span>
          </div>
        ))}
      </div>
    </div>
  );
}