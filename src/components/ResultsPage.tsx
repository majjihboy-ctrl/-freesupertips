import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { fetchRecentResults, type ResultRow } from '../api/football';

export default function ResultsPage() {
  const [results, setResults] = useState<ResultRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentResults(50).then(data => {
      setResults(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="pt-24 pb-16 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <Link to="/" className="text-brand-green hover:underline mb-4 inline-block">← Back to Home</Link>
          <h1 className="text-4xl font-bold text-white mb-2">All Results</h1>
          <p className="text-slate-400">Full history of settled predictions</p>
        </div>

        <div className="overflow-x-auto rounded-2xl shadow-xl border border-bg-surface-hover bg-bg-surface">
          <table className="w-full text-left">
            <thead className="bg-bg-base text-white">
              <tr>
                <th className="px-6 py-5 font-bold text-sm uppercase tracking-wider">Date</th>
                <th className="px-6 py-5 font-bold text-sm uppercase tracking-wider">Match</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Score</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Tip</th>
                <th className="px-6 py-5 text-center font-bold text-sm uppercase tracking-wider">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bg-surface-hover">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading results…
                  </td>
                </tr>
              ) : results.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center text-slate-400">
                    No settled results yet.
                  </td>
                </tr>
              ) : (
                results.map((result, index) => (
                  <tr key={result.id} className={index % 2 === 0 ? 'bg-bg-surface' : 'bg-bg-base/40'}>
                    <td className="px-6 py-5 text-slate-400 font-medium">{result.date}</td>
                    <td className="px-6 py-5 font-bold text-white">{result.homeTeam} vs {result.awayTeam}</td>
                    <td className="px-6 py-5 text-center font-bold text-slate-300">
                      {result.homeScore}-{result.awayScore}
                    </td>
                    <td className="px-6 py-5 text-center text-brand-green font-bold">{result.prediction}</td>
                    <td className="px-6 py-5 text-center">
                      <span
                        className={`inline-block px-4 py-2 rounded-full text-sm font-bold ${
                          result.outcome === 'WON'
                            ? 'bg-brand-green/15 text-brand-green'
                            : result.outcome === 'LOST'
                            ? 'bg-brand-danger/15 text-brand-danger'
                            : 'bg-bg-surface-hover text-slate-400'
                        }`}
                      >
                        {result.outcome}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
