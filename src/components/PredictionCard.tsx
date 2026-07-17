import { type BetSlipItem } from './BetSlip';

interface PredictionCardProps {
  id: number;
  homeTeam: string;
  awayTeam: string;
  prediction: string;
  odds: string;
  confidence: string;
  isPremium: boolean;
  time: string;
  league: string;
  userHasPremium?: boolean;
  onAddToSlip?: (item: BetSlipItem) => void;
  onViewStats?: () => void; // <-- Added this!
}

export default function PredictionCard({
  id, homeTeam, awayTeam, prediction, odds, confidence, isPremium, time, league, userHasPremium = false, onAddToSlip, onViewStats
}: PredictionCardProps) {

  const isLocked = isPremium && !userHasPremium;

  return (
    // Added onClick and cursor-pointer to make the whole card clickable for stats
    <div
      onClick={onViewStats}
      className="relative bg-bg-surface rounded-xl border border-bg-surface-hover overflow-hidden transition-transform hover:-translate-y-1 shadow-lg min-h-[280px] flex flex-col cursor-pointer group"
    >

      {/* Header */}
      <div className="p-3 border-b border-bg-surface-hover flex justify-between items-center bg-bg-base/50">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider truncate">{league}</span>
        <span className="text-xs text-slate-500 whitespace-nowrap ml-2">{time}</span>
      </div>

      {/* Matchup Section */}
      <div className="p-5 flex-grow flex flex-col justify-between">
        <div className="flex flex-col gap-2 mb-6 text-center">
          <div className="text-lg font-bold truncate">{homeTeam}</div>
          <div className="text-sm text-slate-500 font-bold italic">VS</div>
          <div className="text-lg font-bold truncate">{awayTeam}</div>
        </div>

        {/* Prediction / Premium Area */}
        {isLocked ? (
          <div className="relative bg-bg-base p-3 rounded-lg border border-bg-surface-hover overflow-hidden">
            <div className="blur-sm select-none opacity-50">
              <div className="flex justify-between items-center">
                <p className="font-bold text-brand-green text-sm">Hidden Prediction (2.10)</p>
                <p className="font-bold text-sm">{confidence}</p>
              </div>
            </div>
            <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center bg-bg-surface/80 backdrop-blur-[2px]">
              <span className="text-2xl mb-1">🔒</span>
              <h4 className="text-brand-premium font-bold text-sm mb-2">Premium Access</h4>
              <button className="bg-brand-premium hover:bg-yellow-500 text-bg-base px-4 py-1.5 rounded-md font-bold text-xs transition-colors">
                Unlock Now
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-bg-base p-3 rounded-lg border border-bg-surface-hover">
            {/* Top row: Prediction & Confidence */}
            <div className="flex justify-between items-start mb-3">
              <div>
                <p className="text-xs text-slate-400 mb-1">Prediction</p>
                <p className="font-bold text-brand-green text-sm">
                  {prediction} <span className="text-slate-400 font-normal">({odds})</span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-400 mb-1">Confidence</p>
                <p className="font-bold text-sm text-brand-green">{confidence}</p>
              </div>
            </div>

            {/* Bottom row: Add to Bet Slip Button */}
            {/* Added e.stopPropagation() so clicking this doesn't open the modal */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAddToSlip && onAddToSlip({ id, homeTeam, awayTeam, prediction, odds: parseFloat(odds), league });
              }}
              className="w-full bg-bg-surface hover:bg-brand-green hover:text-white text-brand-green border border-brand-green/30 py-2 rounded-md text-xs font-bold transition-all flex items-center justify-center gap-1"
            >
              <span>+</span> Add to Bet Slip
            </button>
          </div>
        )}
      </div>

      {/* Subtle hint that the card is clickable */}
      <div className="absolute top-3 right-3 text-slate-600 group-hover:text-brand-green transition-colors text-[10px] font-bold uppercase tracking-wider opacity-0 group-hover:opacity-100">
        View Stats 📊
      </div>
    </div>
  );
}