import { useParams, Link } from 'react-router-dom';
import DailyPredictions from './DailyPredictions';
import type { Day } from '../api/football';

const VALID_DAYS: Day[] = ['yesterday', 'today', 'tomorrow'];

export default function DayPage() {
  const { day } = useParams();
  const safeDay: Day = VALID_DAYS.includes(day as Day) ? (day as Day) : 'today';

  return (
    <div className="pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <Link to="/" className="text-brand-green hover:underline mb-4 inline-block">← Back to Home</Link>
          <h1 className="text-4xl font-bold text-white mb-2">{safeDay.toUpperCase()} Football Predictions</h1>
          <p className="text-slate-400">Free betting tips for {safeDay}</p>
        </div>
        <DailyPredictions initialDay={safeDay} />
      </div>
    </div>
  );
}