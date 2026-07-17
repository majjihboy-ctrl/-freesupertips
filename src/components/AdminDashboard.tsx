import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase'; // <-- Import Supabase

interface Prediction {
  id: number;
  fixtureId: number;
  prediction: string;
  odds: string;
  confidence: string;
  isPremium: boolean;
}

interface AdminDashboardProps {
  user: User | null;
}

export default function AdminDashboard({ user }: AdminDashboardProps) {
  const navigate = useNavigate();
  const [predictions, setPredictions] = useState<Prediction[]>([]);

  const [formData, setFormData] = useState({
    fixtureId: '',
    prediction: '',
    odds: '',
    confidence: '',
    isPremium: false,
  });
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchPredictions();
  }, []);

  // Fetch from Supabase
  const fetchPredictions = async () => {
    const { data, error } = await supabase.from('predictions').select('*');
    if (error) console.error("Error fetching:", error);
    else setPredictions(data || []);
  };

  // Save to Supabase
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage('');

    if (!formData.fixtureId || !formData.prediction) {
      setMessage('❌ Fixture ID and Prediction are required!');
      return;
    }

    const { error } = await supabase.from('predictions').insert({
      fixtureId: Number(formData.fixtureId),
      prediction: formData.prediction,
      odds: formData.odds,
      confidence: formData.confidence,
      isPremium: formData.isPremium,
    });

    if (error) {
      setMessage('❌ Failed to save: ' + error.message);
    } else {
      setMessage('✅ Prediction added successfully!');
      setFormData({ fixtureId: '', prediction: '', odds: '', confidence: '', isPremium: false });
      fetchPredictions();
    }
  };

  // Delete from Supabase
  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this tip?')) return;

    const { error } = await supabase.from('predictions').delete().eq('fixtureId', id);

    if (error) {
      console.error("Failed to delete", error);
    } else {
      fetchPredictions();
    }
  };

  return (
    <div className="min-h-screen bg-bg-base p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">⚙️ Admin Dashboard</h1>
            <p className="text-slate-400 text-sm mt-1">
              Logged in as: <span className="text-brand-green font-bold">{user?.email}</span>
            </p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="bg-bg-surface hover:bg-bg-surface-hover text-white px-4 py-2 rounded-lg border border-bg-surface-hover transition-colors"
          >
            ← Back to Site
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <div className="bg-bg-surface p-6 rounded-2xl border border-bg-surface-hover sticky top-24">
              <h2 className="text-xl font-bold text-white mb-4">➕ Add New Tip</h2>

              <div className="bg-blue-500/10 border border-blue-500/30 p-3 rounded-lg mb-4">
                <p className="text-xs text-blue-400 font-bold mb-1">💡 HOW TO FIND MATCH ID:</p>
                <p className="text-xs text-slate-300">1. Go to the main site. <br/> 2. Press F12, then open Console. <br/> 3. Look for the "AVAILABLE MATCHES" table and copy the ID.</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-slate-400 uppercase">Match ID *</label>
                  <input
                    type="number"
                    value={formData.fixtureId}
                    onChange={(e) => setFormData({...formData, fixtureId: e.target.value})}
                    className="w-full mt-1 bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                    placeholder="e.g. 1513216"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-400 uppercase">Prediction *</label>
                  <input
                    type="text"
                    value={formData.prediction}
                    onChange={(e) => setFormData({...formData, prediction: e.target.value})}
                    className="w-full mt-1 bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                    placeholder="e.g. Home Win"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase">Odds</label>
                    <input
                      type="text"
                      value={formData.odds}
                      onChange={(e) => setFormData({...formData, odds: e.target.value})}
                      className="w-full mt-1 bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                      placeholder="1.85"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase">Confidence</label>
                    <input
                      type="text"
                      value={formData.confidence}
                      onChange={(e) => setFormData({...formData, confidence: e.target.value})}
                      className="w-full mt-1 bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                      placeholder="75%"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="isPremium"
                    checked={formData.isPremium}
                    onChange={(e) => setFormData({...formData, isPremium: e.target.checked})}
                    className="rounded bg-bg-base border-slate-600 text-brand-green focus:ring-brand-green"
                  />
                  <label htmlFor="isPremium" className="text-sm text-slate-300 cursor-pointer">Lock behind Premium Paywall 🔒</label>
                </div>

                <button type="submit" className="w-full bg-brand-green hover:bg-brand-green-hover text-white font-bold py-3 rounded-lg transition-colors mt-4">
                  Save Prediction
                </button>
              </form>
              {message && <p className="text-center text-sm mt-4 text-brand-green">{message}</p>}
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="bg-bg-surface rounded-2xl border border-bg-surface-hover overflow-hidden">
              <div className="p-4 border-b border-bg-surface-hover bg-bg-base/50">
                <h2 className="text-lg font-bold text-white">📋 Active Predictions ({predictions.length})</h2>
              </div>

              <div className="divide-y divide-bg-surface-hover max-h-[600px] overflow-y-auto">
                {predictions.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">No predictions added yet. Use the form to add your first tip!</div>
                ) : (
                  predictions.map((p) => (
                    <div key={p.id} className="p-4 flex justify-between items-center hover:bg-bg-base/50 transition-colors">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">ID: {p.fixtureId}</span>
                          {p.isPremium && <span className="text-[10px] bg-brand-premium/20 text-brand-premium px-2 py-0.5 rounded font-bold">PREMIUM</span>}
                        </div>
                        <p className="text-sm text-brand-green mt-1">{p.prediction} <span className="text-slate-500">({p.odds})</span></p>
                        <p className="text-xs text-slate-500">Confidence: {p.confidence}</p>
                      </div>
                      <button
                        onClick={() => handleDelete(p.fixtureId)}
                        className="text-slate-500 hover:text-brand-danger bg-bg-base p-2 rounded-lg transition-colors"
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}