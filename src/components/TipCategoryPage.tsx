import { useParams, Link } from 'react-router-dom';
import DailyPredictions from './DailyPredictions';

export default function TipCategoryPage() {
  const { category } = useParams();

  return (
    <div className="pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <Link to="/" className="text-[#F6017C] hover:underline mb-4 inline-block">← Back to Home</Link>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">{category?.replace(/-/g, ' ').toUpperCase()} Tips</h1>
          <p className="text-gray-600">Specialized predictions for {category}</p>
        </div>
        <DailyPredictions />
      </div>
    </div>
  );
}