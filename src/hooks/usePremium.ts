import { useState, useEffect, useRef } from 'react';
import { supabase } from '../lib/supabase';

export function usePremium(userId: string | null) {
  const [hasPremium, setHasPremium] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPremiumStatus = async (id: string) => {
    const { data, error } = await supabase
      .from('profiles')
      .select('is_premium')
      .eq('id', id)
      .maybeSingle();

    if (!error && data) {
      setHasPremium(data.is_premium);
      return data.is_premium as boolean;
    }
    setHasPremium(false);
    return false;
  };

  useEffect(() => {
    if (userId) {
      void fetchPremiumStatus(userId);
    } else {
      setHasPremium(false);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [userId]);

  // Polls for up to ~2 minutes after a payment is triggered, since the
  // M-Pesa callback lands asynchronously (the user enters their PIN on
  // their phone, which can take anywhere from a few seconds to a minute+).
  // A blind fixed-delay reload would either fire too early (still pending)
  // or leave the user waiting needlessly if it completes sooner.
  const pollForPremium = (id: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    let attempts = 0;
    pollRef.current = setInterval(async () => {
      attempts += 1;
      const granted = await fetchPremiumStatus(id);
      if (granted || attempts >= 24) {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }, 5000);
  };

    const handleUpgradeToPremium = async (onShowAuth: () => void) => {
    if (!userId) {
      onShowAuth();
      return;
    }

    // Defaulting to the Weekly Plan (500 KES) from the Navbar
    const amount = 500;

    const phone = prompt(`Enter your M-Pesa Phone Number for Weekly VIP (${amount} KES):`);
    if (!phone) return;
    if (!phone.startsWith('254') || phone.length !== 12) {
      alert("Please enter a valid phone number in the format 2547XXXXXXXX");
      return;
    }
    try {
      const res = await fetch('/api/mpesa/stkpush', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, amount, userId, plan: 'weekly' }),
      });
      const data = await res.json();
      if (data.success) {
        alert(`✅ Check your phone! Enter M-Pesa PIN to pay ${amount} KES.`);
        pollForPremium(userId);
      } else {
        alert("❌ Failed to initiate M-Pesa. Please try again.");
      }
    } catch (error) {
      console.error("M-Pesa Error:", error);
    }
  };

  return { hasPremium, handleUpgradeToPremium, pollForPremium };
}