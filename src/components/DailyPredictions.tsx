import { useState, useEffect } from 'react';
import { Calendar, TrendingUp, Crown, Loader2 } from 'lucide-react';
import { fetchFixturesForDay, type Fixture, type Day } from '../api/football';

interface DailyPredictionsProps {
  initialDay?: Day;
}

export default function DailyPredictions({ initialDay = 'today' }: DailyPredictionsProps) {
  const [activeDay, setActiveDay] = useState<Day>(initialDay);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(true);
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchFixturesForDay(activeDay).then((data) => {
      if (!cancelled) {
        setFixtures(data);
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, [activeDay]);

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">Free Sure Tips For Today</h2>
          <p className="text-gray-500 flex items-center justify-center gap-2 text-lg">
            <Calendar className="w-5 h-5 text-primary" />
            {today}
          </p>
        </div>

        {/* Day Tabs */}
        <div className="flex justify-center mb-10">
          <div className="bg-gray-100 rounded-full p-1.5 inline-flex gap-1">
            {(['yesterday', 'today', 'tomorrow'] as Day[]).map((day) => (
              <button
                key={day}
                onClick={() => setActiveDay(day)}
                className={`px-6 py-2.5 rounded-full font-semibold capitalize transition-all text-sm ${
                  activeDay === day
                    ? 'bg-primary text-white shadow-md'
                    : 'text-gray-600 hover:text-primary'
                }`}
              >
                {day}
              </button>
            ))}
          </div>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-wrap justify-center gap-4 mb-10">
          <a href="/pricing" className="px-8 py-3.5 bg-primary text-white rounded-full font-bold hover:bg-primary-hover transition-all shadow-lg flex items-center gap-2 hover:-translate-y-0.5">
            <Crown className="w-5 h-5" />
            JOIN VIP TIPS
          </a>
          <a href="/pricing" className="px-8 py-3.5 bg-gradient-to-r from-yellow-400 to-orange-500 text-white rounded-full font-bold hover:from-yellow-500 hover:to-orange-600 transition-all shadow-lg hover:-translate-y-0.5">
            TODAY'S BANKER
          </a>
        </div>

        {/* Predictions Table */}
        <div className="overflow-x-auto rounded-2xl shadow-xl border border-gray-100 bg-white">
          <table className="w-full text-left">
            <thead className="bg-gray-900 text-white">
              <tr>
                <th className="px-6 py-5 font-bold text-sm uppercase tracking-wider">League / Game</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Score</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Tips</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Odds</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Probability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading matches…
                  </td>
                </tr>
              ) : fixtures.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                    No matches scraped for {activeDay} yet. Run the scraper to populate this day.
                  </td>
                </tr>
              ) : (
                fixtures.map((match, index) => (
                  <tr
                    key={match.id}
                    className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-pink-50/30 transition-colors`}
                  >
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center text-xl">⚽</div>
                        <div>
                          <div className="text-sm text-gray-500 font-medium">{match.league} • {match.time}</div>
                          <div className="font-bold text-gray-900 text-base mt-0.5">{match.homeTeam} vs {match.awayTeam}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5 text-center font-bold text-gray-400 text-lg">
                      {match.homeScore !== null && match.awayScore !== null ? `${match.homeScore}-${match.awayScore}` : '-'}
                    </td>
                    <td className="px-6 py-5 text-center">
                      {match.isPremium ? (
                        <a href="/pricing" className="inline-block px-4 py-2 rounded-full font-bold text-sm shadow-sm bg-gradient-to-r from-yellow-400 to-orange-500 text-white">
                          🔒 VIP Only
                        </a>
                      ) : (
                        <span className="inline-block px-4 py-2 rounded-full font-bold text-sm shadow-sm bg-primary text-white">
                          {match.prediction}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-5 text-center font-extrabold text-primary text-lg">{match.odds}</td>
                    <td className="px-6 py-5 text-center">
                      <div className="inline-flex items-center gap-1.5 bg-green-50 text-green-700 px-3 py-1.5 rounded-full font-bold text-sm">
                        <TrendingUp className="w-4 h-4" />
                        {match.confidence}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
