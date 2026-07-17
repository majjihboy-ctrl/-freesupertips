import { useState, useEffect } from 'react';
import { type Fixture } from '../api/football';
import { supabase } from '../lib/supabase';

interface MatchStatsModalProps {
  match: Fixture | null;
  onClose: () => void;
}

export default function MatchStatsModal({ match, onClose }: MatchStatsModalProps) {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'form' | 'predictions' | 'details'>('form');

  useEffect(() => {
    if (!match) return;
    const fetchStats = async () => {
      setLoading(true);
      const { data } = await supabase.from('match_stats').select('*').eq('fixture_id', match.id).maybeSingle();
      if (data) setStats(data);
      setLoading(false);
    };
    fetchStats();
  }, [match]);

  if (!match) return null;

  const getFormResult = (fixture: any, teamId: number) => {
    const isHome = fixture.home_team_id === teamId;
    const goalsFor = isHome ? fixture.home_score : fixture.away_score;
    const goalsAgainst = isHome ? fixture.away_score : fixture.home_score;
    if (goalsFor === null || goalsAgainst === null) return { label: '?', color: 'bg-slate-700 text-slate-400' };
    if (goalsFor > goalsAgainst) return { label: 'W', color: 'bg-brand-green text-white' };
    if (goalsFor < goalsAgainst) return { label: 'L', color: 'bg-brand-danger text-white' };
    return { label: 'D', color: 'bg-slate-500 text-white' };
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-bg-surface w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-bg-surface-hover shadow-2xl relative" onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="sticky top-0 bg-bg-surface border-b border-bg-surface-hover p-6 flex justify-between items-center z-10">
          <div className="text-center flex-1">
            <h2 className="text-2xl font-bold text-white">{match.homeTeam} <span className="text-slate-500 mx-2">vs</span> {match.awayTeam}</h2>
            <p className="text-sm text-slate-400 mt-1">{match.league} • {match.time}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl leading-none px-4">✕</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-bg-surface-hover">
          {(['form', 'predictions', 'details'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-4 text-sm font-bold uppercase tracking-wider transition-colors ${
                activeTab === tab ? 'text-brand-green border-b-2 border-brand-green bg-brand-green/5' : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab === 'form' ? '📈 Form & H2H' : tab === 'predictions' ? '🤖 ML Predictions' : '🏟️ Match Details'}
            </button>
          ))}
        </div>

        <div className="p-6">
          {loading ? (
            <div className="text-center py-12 text-slate-400 animate-pulse">Loading advanced statistics...</div>
          ) : !stats ? (
            <div className="text-center py-12 text-slate-400">Stats not available for this match yet.</div>
          ) : (
            <>
              {/* TAB 1: FORM & H2H */}
              {activeTab === 'form' && (
                <div className="space-y-8">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-bg-base/50 rounded-xl p-4 border border-bg-surface-hover">
                      <h4 className="font-bold text-brand-green mb-3">{match.homeTeam} (Last 5)</h4>
                      <div className="flex gap-2 flex-wrap">
                        {stats.home_form?.map((f: any, i: number) => {
                          const form = getFormResult(f, match.homeTeamId);
                          return <span key={i} className={`w-8 h-8 flex items-center justify-center rounded-full font-bold text-sm ${form.color}`}>{form.label}</span>;
                        })}
                      </div>
                    </div>
                    <div className="bg-bg-base/50 rounded-xl p-4 border border-bg-surface-hover">
                      <h4 className="font-bold text-blue-400 mb-3">{match.awayTeam} (Last 5)</h4>
                      <div className="flex gap-2 flex-wrap">
                        {stats.away_form?.map((f: any, i: number) => {
                          const form = getFormResult(f, match.awayTeamId);
                          return <span key={i} className={`w-8 h-8 flex items-center justify-center rounded-full font-bold text-sm ${form.color}`}>{form.label}</span>;
                        })}
                      </div>
                    </div>
                  </div>
                  {stats.h2h_data?.length > 0 && (
                    <div>
                      <h3 className="text-lg font-bold text-white mb-4">⚔️ Head to Head</h3>
                      <div className="bg-bg-base/50 rounded-xl border border-bg-surface-hover overflow-hidden divide-y divide-bg-surface-hover">
                        {stats.h2h_data.map((f: any, i: number) => (
                          <div key={i} className="p-4 flex justify-between items-center">
                            <span className="text-xs text-slate-500 w-24">{new Date(f.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                            <div className="flex-1 flex justify-center items-center gap-4 font-semibold text-white">
                              <span className="text-right flex-1">{f.home}</span>
                              <span className="bg-bg-surface px-3 py-1 rounded border border-bg-surface-hover font-bold text-brand-premium">{f.score}</span>
                              <span className="flex-1">{f.away}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: ML PREDICTIONS & ODDS */}
              {activeTab === 'predictions' && stats.prediction_data && (
                <div className="space-y-6">
                  <div className="bg-brand-premium/10 border border-brand-premium/30 rounded-xl p-6 text-center">
                    <p className="text-sm text-slate-400 uppercase tracking-wider font-bold mb-2">AI Most Likely Score</p>
                    <p className="text-4xl font-black text-white">{stats.prediction_data.markets?.score?.most_likely || 'N/A'}</p>
                    <p className="text-brand-green font-bold mt-2">Confidence: {Math.round((stats.prediction_data.model?.confidence || 0) * 100)}%</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-bg-base/50 rounded-xl p-4 border border-bg-surface-hover">
                      <h4 className="font-bold text-white mb-3">Both Teams to Score</h4>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Probability</span>
                        <span className="text-white font-bold">{stats.prediction_data.markets?.btts?.prob_yes}%</span>
                      </div>
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-slate-400">Best Odds (Yes)</span>
                        <span className="text-brand-green font-bold">{stats.odds_data?.odds?.btts_yes || '-'}</span>
                      </div>
                    </div>
                    <div className="bg-bg-base/50 rounded-xl p-4 border border-bg-surface-hover">
                      <h4 className="font-bold text-white mb-3">Over 2.5 Goals</h4>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Probability</span>
                        <span className="text-white font-bold">{stats.prediction_data.markets?.over_under?.prob_over_25}%</span>
                      </div>
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-slate-400">Best Odds (Over)</span>
                        <span className="text-brand-green font-bold">{stats.odds_data?.odds?.over_25_goals || '-'}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: MATCH DETAILS */}
              {activeTab === 'details' && stats.match_details && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-bg-base/50 rounded-xl p-4 border border-bg-surface-hover">
                      <h4 className="font-bold text-white mb-3 flex items-center gap-2">🏟️ Venue & Weather</h4>
                      <p className="text-slate-300">{stats.match_details.venue_id ? 'Stadium ID: ' + stats.match_details.venue_id : 'Venue TBA'}</p>
                      {stats.match_details.weather?.description && (
                        <p className="text-slate-300 mt-2 capitalize">
                          🌤️ {stats.match_details.weather.description}, {stats.match_details.weather.temperature_c}°C, Wind: {stats.match_details.weather.wind_speed} km/h
                        </p>
                      )}
                    </div>
                    <div className="bg-bg-base/50 rounded-xl p-4 border border-bg-surface-hover">
                      <h4 className="font-bold text-white mb-3 flex items-center gap-2">👨‍⚖️ Referee</h4>
                      <p className="text-slate-300">Referee ID: {stats.match_details.referee_id || 'TBA'}</p>
                      <p className="text-xs text-slate-500 mt-2">(Referee name stats coming in Phase 2)</p>
                    </div>
                  </div>

                  {stats.lineups_data?.lineup_status && (
                    <div className="bg-bg-base/50 rounded-xl p-4 border border-bg-surface-hover">
                      <h4 className="font-bold text-white mb-3 flex items-center gap-2">👕 Lineups</h4>
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold uppercase ${
                        stats.lineups_data.lineup_status === 'confirmed' ? 'bg-brand-green/20 text-brand-green' :
                        stats.lineups_data.lineup_status === 'predicted' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-slate-700 text-slate-400'
                      }`}>
                        {stats.lineups_data.lineup_status}
                      </span>
                      <p className="text-xs text-slate-500 mt-2">Full player lists will be displayed here when available.</p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}