export default function SEOContent() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-8 text-center">How We Make Accurate Football Predictions</h2>

        <div className="prose prose-lg max-w-none text-gray-600 space-y-8">
          <div>
            <h3 className="text-2xl font-bold text-gray-900 mb-4">Data-Driven Analysis</h3>
            <p className="leading-relaxed">
              Our predictions are based on comprehensive statistical analysis of team performance, head-to-head records,
              current form, injuries, and tactical matchups. We don't rely on guesswork—every tip is backed by hard data
              and years of football expertise.
            </p>
          </div>

          <div>
            <h3 className="text-2xl font-bold text-gray-900 mb-4">Why Trust Our Predictions?</h3>
            <p className="leading-relaxed">
              With over 85% accuracy rate and thousands of satisfied users worldwide, we've proven our methodology works.
              Our team of expert analysts monitors every major league 24/7 to bring you the most reliable betting tips available.
            </p>
          </div>

          <div>
            <h3 className="text-2xl font-bold text-gray-900 mb-4">Betting Strategy Tips</h3>
            <ul className="list-disc pl-6 space-y-3">
              <li className="leading-relaxed"><strong className="text-gray-900">Single Bets vs Accumulators:</strong> While accumulators offer bigger payouts, single bets provide more consistent returns. We recommend a mix of both.</li>
              <li className="leading-relaxed"><strong className="text-gray-900">Bankroll Management:</strong> Never bet more than 5% of your total bankroll on a single tip.</li>
              <li className="leading-relaxed"><strong className="text-gray-900">Focus on Value:</strong> Look for tips where the probability exceeds the odds offered.</li>
              <li className="leading-relaxed"><strong className="text-gray-900">Stay Disciplined:</strong> Don't chase losses. Stick to the strategy and trust the process.</li>
            </ul>
          </div>

          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-8 rounded-r-lg">
            <p className="font-bold text-gray-900 text-lg mb-3">⚠️ Responsible Gambling Disclaimer</p>
            <p className="text-base leading-relaxed">
              Betting involves risk. Never bet money you cannot afford to lose. Our tips are for entertainment purposes.
              If you have a gambling problem, please seek help from professional organizations like BeGambleAware.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}