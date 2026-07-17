import { useState } from 'react';
import { Calendar, TrendingUp, Crown } from 'lucide-react';

const mockPredictions = [
  { id: 1, league: 'Premier League', time: '15:00', homeTeam: 'Manchester City', awayTeam: 'Arsenal', tip: 'Over 2.5', odds: '1.85', probability: '85%', isBanker: true },
  { id: 2, league: 'La Liga', time: '18:30', homeTeam: 'Real Madrid', awayTeam: 'Barcelona', tip: 'Home(1)', odds: '2.10', probability: '78%', isBanker: false },
  { id: 3, league: 'Serie A', time: '20:45', homeTeam: 'AC Milan', awayTeam: 'Inter Milan', tip: 'BTTS', odds: '1.70', probability: '82%', isBanker: false },
];

export default function DailyPredictions() {
  const [activeDay, setActiveDay] = useState('today');
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

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
            {['yesterday', 'today', 'tomorrow'].map((day) => (
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
          <button className="px-8 py-3.5 bg-primary text-white rounded-full font-bold hover:bg-primary-hover transition-all shadow-lg flex items-center gap-2 hover:-translate-y-0.5">
            <Crown className="w-5 h-5" />
            JOIN VIP TIPS
          </button>
          <button className="px-8 py-3.5 bg-gradient-to-r from-yellow-400 to-orange-500 text-white rounded-full font-bold hover:from-yellow-500 hover:to-orange-600 transition-all shadow-lg hover:-translate-y-0.5">
            TODAY'S BANKER
          </button>
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
              {mockPredictions.map((match, index) => (
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
                  <td className="px-6 py-5 text-center font-bold text-gray-400 text-lg">-</td>
                  <td className="px-6 py-5 text-center">
                    <span className={`inline-block px-4 py-2 rounded-full font-bold text-sm shadow-sm ${
                      match.isBanker 
                        ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-white' 
                        : 'bg-primary text-white'
                    }`}>
                      {match.tip}
                    </span>
                  </td>
                  <td className="px-6 py-5 text-center font-extrabold text-primary text-lg">{match.odds}</td>
                  <td className="px-6 py-5 text-center">
                    <div className="inline-flex items-center gap-1.5 bg-green-50 text-green-700 px-3 py-1.5 rounded-full font-bold text-sm">
                      <TrendingUp className="w-4 h-4" />
                      {match.probability}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}