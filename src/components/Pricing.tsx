import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useState } from 'react';
import { usePremium } from '../hooks/usePremium';

export default function Pricing() {
  const navigate = useNavigate();
  const [loadingPlan, setLoadingPlan] = useState<number | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const { pollForPremium } = usePremium(currentUserId);

  const handleUpgrade = async (amount: number, planName: string, planSlug: 'daily' | 'weekly' | 'monthly') => {
    setLoadingPlan(amount);
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      alert("Please log in first to subscribe!");
      navigate('/');
      setLoadingPlan(null);
      return;
    }
    setCurrentUserId(user.id);

    const phone = prompt(`Enter your M-Pesa Phone Number for ${planName} (${amount} KES):`);
    if (!phone) { setLoadingPlan(null); return; }

    if (!phone.startsWith('254') || phone.length !== 12) {
      alert("Please enter a valid number in the format 2547XXXXXXXX");
      setLoadingPlan(null);
      return;
    }

    try {
      const res = await fetch('/api/mpesa/stkpush', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, amount, userId: user.id, plan: planSlug }),
      });

      const data = await res.json();
      if (data.success) {
        alert(`✅ Check your phone! Enter M-Pesa PIN to pay ${amount} KES. We'll unlock VIP automatically once it's confirmed.`);
        pollForPremium(user.id);
      } else {
        alert("❌ Failed to initiate M-Pesa. Please try again.");
      }
    } catch (error) {
      console.error("M-Pesa Error:", error);
    } finally {
      setLoadingPlan(null);
    }
  };

  return (
    <div className="py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-4">Unlock VIP Predictions</h1>
        <p className="text-slate-400 max-w-2xl mx-auto">Get access to our expertly analyzed premium tips, hand-picked daily.</p>
      </div>

      <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-6">

        {/* 1. DAILY PLAN */}
        <div className="bg-bg-surface p-6 rounded-2xl border border-bg-surface-hover flex flex-col">
          <h3 className="text-xl font-bold text-white mb-1">Daily VIP</h3>
          <p className="text-slate-400 text-sm mb-4">Perfect for weekend punters.</p>
          <p className="text-4xl font-bold text-white mb-1">KES 100</p>
          <p className="text-sm text-slate-500 mb-6">Valid for 24 Hours</p>
          <ul className="space-y-3 mb-8 text-slate-300 text-sm flex-1">
            <li className="flex items-center gap-2">✅ All VIP Picks for the Day</li>
            <li className="flex items-center gap-2">✅ Expert-Analyzed Picks</li>
            <li className="flex items-center gap-2 text-slate-500">❌ Weekly Analysis</li>
          </ul>
          <button
            onClick={() => handleUpgrade(100, 'Daily VIP', 'daily')}
            disabled={loadingPlan === 100}
            className="w-full py-3 rounded-lg border border-bg-surface-hover text-slate-300 font-bold hover:bg-bg-surface-hover transition-colors disabled:opacity-50"
          >
            {loadingPlan === 100 ? 'Processing...' : 'Buy Daily'}
          </button>
        </div>

        {/* 2. WEEKLY PLAN (Highlighted) */}
        <div className="bg-bg-surface p-6 rounded-2xl border-2 border-brand-green relative shadow-lg shadow-brand-green/10 flex flex-col transform md:-translate-y-4">
          <div className="absolute top-0 right-0 bg-brand-green text-white text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-2xl">
            MOST POPULAR
          </div>
          <h3 className="text-xl font-bold text-white mb-1">Weekly VIP</h3>
          <p className="text-slate-400 text-sm mb-4">Best value for regular bettors.</p>
          <p className="text-4xl font-bold text-white mb-1">KES 500</p>
          <p className="text-sm text-slate-500 mb-6">Valid for 7 Days</p>
          <ul className="space-y-3 mb-8 text-slate-300 text-sm flex-1">
            <li className="flex items-center gap-2">✅ <strong className="text-brand-green">Everything in Daily</strong></li>
            <li className="flex items-center gap-2">✅ Hand-Picked VIP Tips</li>
            <li className="flex items-center gap-2">✅ Advanced Match Stats</li>
          </ul>
          <button
            onClick={() => handleUpgrade(500, 'Weekly VIP', 'weekly')}
            disabled={loadingPlan === 500}
            className="w-full py-3 rounded-lg bg-brand-green hover:bg-brand-green-hover text-white font-bold transition-colors disabled:opacity-50"
          >
            {loadingPlan === 500 ? 'Processing...' : 'Buy Weekly'}
          </button>
        </div>

        {/* 3. MONTHLY PLAN */}
        <div className="bg-bg-surface p-6 rounded-2xl border border-bg-surface-hover flex flex-col">
          <h3 className="text-xl font-bold text-white mb-1">Monthly VIP</h3>
          <p className="text-slate-400 text-sm mb-4">For the serious high-roller.</p>
          <p className="text-4xl font-bold text-white mb-1">KES 1,500</p>
          <p className="text-sm text-slate-500 mb-6">Valid for 30 Days</p>
          <ul className="space-y-3 mb-8 text-slate-300 text-sm flex-1">
            <li className="flex items-center gap-2">✅ <strong className="text-brand-green">Everything in Weekly</strong></li>
            <li className="flex items-center gap-2">✅ Priority Support</li>
            <li className="flex items-center gap-2">✅ 1-on-1 Betting Advice</li>
          </ul>
          <button
            onClick={() => handleUpgrade(1500, 'Monthly VIP', 'monthly')}
            disabled={loadingPlan === 1500}
            className="w-full py-3 rounded-lg border border-bg-surface-hover text-slate-300 font-bold hover:bg-bg-surface-hover transition-colors disabled:opacity-50"
          >
            {loadingPlan === 1500 ? 'Processing...' : 'Buy Monthly'}
          </button>
        </div>

      </div>
    </div>
  );
}