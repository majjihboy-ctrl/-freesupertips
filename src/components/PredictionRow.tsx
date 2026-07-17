import { Clock, TrendingUp, ShieldCheck, Crown, ChevronRight } from 'lucide-react';
import { type Fixture } from '../api/football';

interface PredictionRowProps extends Fixture {
  userHasPremium: boolean;
  onViewStats: () => void;
}

export default function PredictionRow({
  homeTeam,
  awayTeam,
  league,
  time,
  prediction,
  odds,
  confidence,
  isPremium,
  onViewStats
}: PredictionRowProps) {
  const hasExpertTip = prediction && prediction !== 'Awaiting Expert Analysis';

  return (
    <div
      onClick={onViewStats}
      className="group flex flex-col sm:flex-row sm:items-center justify-between p-4 sm:px-6 hover:bg-slate-800/40 transition-all duration-200 cursor-pointer border-b border-slate-800/50 last:border-0"
    >
      {/* Left: Time & League (Mobile: Top, Desktop: Left) */}
      <div className="flex items-center gap-3 mb-3 sm:mb-0 sm:w-48 shrink-0">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 bg-slate-900/80 px-2.5 py-1.5 rounded-md border border-slate-800">
          <Clock className="w-3.5 h-3.5" />
          <span>{time}</span>
        </div>
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider truncate hidden sm:block">
          {league}
        </span>
      </div>

      {/* Middle: Teams */}
      <div className="flex-1 flex items-center justify-between sm:justify-center gap-4 mb-3 sm:mb-0 px-2">
        <span className="text-base sm:text-lg font-bold text-slate-100 text-right sm:text-right flex-1 truncate group-hover:text-white transition-colors">
          {homeTeam}
        </span>
        <span className="text-xs font-black text-slate-600 tracking-widest px-2">VS</span>
        <span className="text-base sm:text-lg font-bold text-slate-100 text-left sm:text-left flex-1 truncate group-hover:text-white transition-colors">
          {awayTeam}
        </span>
      </div>

      {/* Right: Insights & Action */}
      <div className="flex items-center gap-3 sm:w-80 justify-end">

        {/* Odds Badge */}
        <div className="hidden sm:flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 w-24 justify-center">
          <TrendingUp className="w-4 h-4 text-emerald-500" />
          <div className="flex flex-col items-center">
            <span className="text-[10px] uppercase text-slate-500 font-semibold">Odds</span>
            <span className="text-sm font-bold text-slate-200">{odds}</span>
          </div>
        </div>

        {/* Prediction Badge */}
        <div className={`flex items-center gap-2 rounded-lg px-3 py-2 border flex-1 sm:flex-initial min-w-[140px] transition-colors ${
          isPremium 
            ? 'bg-amber-500/10 border-amber-500/30' 
            : hasExpertTip 
              ? 'bg-emerald-500/10 border-emerald-500/30' 
              : 'bg-slate-900/50 border-slate-800'
        }`}>
          {isPremium ? (
            <Crown className="w-4 h-4 text-amber-400 shrink-0" />
          ) : hasExpertTip ? (
            <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
          ) : (
            <Clock className="w-4 h-4 text-slate-500 shrink-0" />
          )}
          <div className="flex flex-col min-w-0">
            <span className="text-[10px] uppercase font-semibold tracking-wider truncate text-slate-400">
              {isPremium ? 'VIP Pick' : hasExpertTip ? 'Expert Tip' : 'Status'}
            </span>
            <span className={`text-sm font-bold truncate ${
              isPremium ? 'text-amber-400' : hasExpertTip ? 'text-emerald-400' : 'text-slate-500'
            }`}>
              {hasExpertTip ? `${prediction} • ${confidence}` : 'Awaiting Analysis'}
            </span>
          </div>
        </div>

        {/* Chevron Action Indicator */}
        <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-slate-300 group-hover:translate-x-1 transition-all shrink-0" />
      </div>
    </div>
  );
}