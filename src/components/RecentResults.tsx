import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { fetchRecentResults, type ResultRow } from '../api/football';

export default function RecentResults() {
  const [results, setResults] = useState<ResultRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentResults(15).then((data) => {
      setResults(data);
      setLoading(false);
    });
  }, []);

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-center text-gray-900 mb-12">Our Recent Winning Tips</h2>

        <div className="overflow-x-auto rounded-2xl shadow-xl border border-gray-100 bg-white">
          <table className="w-full text-left">
            <thead className="bg-gray-900 text-white">
              <tr>
                <th className="px-6 py-5 font-bold text-sm uppercase tracking-wider">Date</th>
                <th className="px-6 py-5 font-bold text-sm uppercase tracking-wider">Match</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Score</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Tip</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Odds</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading results…
                  </td>
                </tr>
              ) : results.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                    No settled results yet — the scraper needs to run after matches finish.
                  </td>
                </tr>
              ) : (
                results.map((result, index) => (
                  <tr
                    key={result.id}
                    className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-pink-50/30 transition-colors cursor-pointer`}
                  >
                    <td className="px-6 py-5 text-gray-600 font-medium">{result.date}</td>
                    <td className="px-6 py-5 font-bold text-gray-900">{result.homeTeam} vs {result.awayTeam}</td>
                    <td className="px-6 py-5 text-center font-bold text-gray-700 text-lg">
                      {result.homeScore}-{result.awayScore}
                    </td>
                    <td className="px-6 py-5 text-center">
                      <span className="inline-block px-4 py-2 bg-primary text-white rounded-full text-sm font-bold">
                        {result.prediction}
                      </span>
                    </td>
                    <td className="px-6 py-5 text-center font-extrabold text-primary text-lg">{result.odds}</td>
                    <td className="px-6 py-5 text-center">
                      <span className={`inline-block px-4 py-2 rounded-full text-sm font-bold shadow-sm ${
                        result.outcome === 'WON' ? 'bg-green-100 text-green-700' :
                        result.outcome === 'LOST' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {result.outcome}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="text-center mt-10">
          <Link to="/day/yesterday" className="inline-flex items-center text-primary font-bold text-lg hover:underline">
            View More Results →
          </Link>
        </div>
      </div>
    </section>
  );
}
