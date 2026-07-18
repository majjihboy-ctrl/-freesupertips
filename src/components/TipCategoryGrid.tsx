import { Link } from 'react-router-dom';

const tipCategories = [
  'Home Win', 'Away Win', 'BTTS/GG',
  'Over 2.5', 'Draws',
];

export default function TipCategoryGrid() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-bg-base">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-center text-white mb-12">Free Prediction Stores</h2>

        {/* Tip Categories */}
        <div className="flex flex-wrap justify-center gap-3">
          {tipCategories.map((category) => (
            <Link
              key={category}
              to={`/tips/${category.toLowerCase().replace(/\s+/g, '-')}`}
              className="px-6 py-3 bg-bg-surface border-2 border-bg-surface-hover rounded-full font-semibold text-slate-300 hover:border-brand-green hover:text-brand-green transition-all shadow-sm hover:shadow-md"
            >
              {category}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}