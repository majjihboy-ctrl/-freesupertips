import { Link } from 'react-router-dom';

const tipCategories = [
  'Banker', 'Home Win', 'Away Win', 'BTTS/GG', 'Double Chance',
  'HT 0.5', 'Over 1.5', 'Over 2.5', 'Under 3.5', 'Draws',
  'Draw No Bet', 'Single Bets', 'Win Either Half', 'Correct Scores'
];

const packages = ['Free 2 Odds', 'Free 3 Odds', 'Free 5 Odds'];

export default function TipCategoryGrid() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-center text-gray-900 mb-12">Free Prediction Stores</h2>

        {/* Tip Categories */}
        <div className="flex flex-wrap justify-center gap-3 mb-10">
          {tipCategories.map((category) => (
            <Link
              key={category}
              to={`/category/${category.toLowerCase().replace(/\s+/g, '-')}`}
              className="px-6 py-3 bg-white border-2 border-gray-200 rounded-full font-semibold text-gray-700 hover:border-primary hover:text-primary transition-all shadow-sm hover:shadow-md"
            >
              {category}
            </Link>
          ))}
        </div>

        {/* Package Links */}
        <div className="flex flex-wrap justify-center gap-4">
          {packages.map((pkg) => (
            <Link
              key={pkg}
              to={`/category/${pkg.toLowerCase().replace(/\s+/g, '-')}`}
              className="px-8 py-3.5 bg-primary text-white rounded-full font-bold hover:bg-primary-hover transition-all shadow-lg hover:-translate-y-0.5"
            >
              {pkg}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}