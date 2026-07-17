import { Link } from 'react-router-dom';

const mockResults = [
  { id: 1, date: '2024-01-15', homeTeam: 'Liverpool', awayTeam: 'Chelsea', score: '2-1', tip: 'Home(1)', odds: '1.95', status: 'WON' },
  { id: 2, date: '2024-01-14', homeTeam: 'Bayern Munich', awayTeam: 'Dortmund', score: '3-2', tip: 'Over 2.5', odds: '1.75', status: 'WON' },
  { id: 3, date: '2024-01-13', homeTeam: 'PSG', awayTeam: 'Lyon', score: '1-1', tip: 'Home(1)', odds: '1.50', status: 'LOST' },
  { id: 4, date: '2024-01-12', homeTeam: 'Juventus', awayTeam: 'Napoli', score: '2-0', tip: 'Home(1)', odds: '2.10', status: 'WON' },
];

export default function RecentResults() {
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
              {mockResults.map((result, index) => (
                <tr
                  key={result.id}
                  className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-pink-50/30 transition-colors cursor-pointer`}
                >
                  <td className="px-6 py-5 text-gray-600 font-medium">{result.date}</td>
                  <td className="px-6 py-5 font-bold text-gray-900">{result.homeTeam} vs {result.awayTeam}</td>
                  <td className="px-6 py-5 text-center font-bold text-gray-700 text-lg">{result.score}</td>
                  <td className="px-6 py-5 text-center">
                    <span className="inline-block px-4 py-2 bg-primary text-white rounded-full text-sm font-bold">
                      {result.tip}
                    </span>
                  </td>
                  <td className="px-6 py-5 text-center font-extrabold text-primary text-lg">{result.odds}</td>
                  <td className="px-6 py-5 text-center">
                    <span className={`inline-block px-4 py-2 rounded-full text-sm font-bold shadow-sm ${
                      result.status === 'WON' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {result.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="text-center mt-10">
          <Link to="/results" className="inline-flex items-center text-primary font-bold text-lg hover:underline">
            View More Results →
          </Link>
        </div>
      </div>
    </section>
  );
}