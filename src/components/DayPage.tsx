import { useParams, Link } from 'react-router-dom';
import DailyPredictions from './DailyPredictions';

export default function DayPage() {
  const { day } = useParams();

  return (
    <div className="pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <Link to="/" className="text-brand-green hover:underline mb-4 inline-block">← Back to Home</Link>
          <h1 className="text-4xl font-bold text-white mb-2">{day?.toUpperCase()} Football Predictions</h1>
          <p className="text-slate-400">Free betting tips for {day}</p>
        </div>
        <DailyPredictions />
      </div>
    </div>
  );
}